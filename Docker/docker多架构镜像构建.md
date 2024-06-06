[TOC]

# Docker多架构镜像构建实战记录

## 1. 问题场景

基于K3S构建的私有容器云环境中，当前存在linux/amd64(Intel X86_64),linux/arm64(飞腾CPU+银河麒麟V10系统),linux/mips64le(龙芯CPU+中标麒麟V5) 三种架构的机器。在这个环境中部署的java服务镜像需要支持在三种架构的机器上都能运行，因此需要制作多架构镜像。

多架构镜像其实是在registry中保存了多个架构的镜像，但将它们的manifest合并到了同一个index中。主机节点从registry拉取镜像时，会自动识别拉取与本机架构相同的镜像。因此可以解决镜像在多种架构节点运行的问题。

下文记录构建多架构镜像的实战过程。

## 2. 基于docker manifest构建多架构debian基础镜像

构建java服务镜像所需的基础镜像需要支持多架构，以便我们基于不同架构的基础镜像构建服务镜像。

经在docker hub中查找，bullseye版本的debian官方镜像能够同时支持以上三种架构，较早版本如stretch、buster没有mips64le架构的镜像，因此选用bullseye版debian镜像作为基础镜像。

私有云环境不能连接公网，因此需要把镜像从公网下载保存后再拷入内网。

```shell
# 从docker hub拉取debian官方mips64le架构镜像
docker pull debian:bullseye --platform linux/mips64le

# 保存镜像到本地
docker save -o debian-bullseye-mips64le.tar debian:bullseye

# 把镜像从本地删除，否则会与之后pull的其他架构镜像重名
docker image rm debian:bullseye

# 同以上步骤操作linux/arm64与linux/amd64架构镜像。
```

将以上三种镜像的tar文件拷入内网，在内网主机上执行以下操作。

```shell
# load linux/mips64le架构debian镜像
docer load -i debian-bullseye-mips64le.tar

# 给镜像重新打tag以便推到私有registry
docker tag debian:bullseye 192.168.41.96:5000/debiain:bullseye-mips64le

# 推送镜像到私有registry
docker push 192.168.41.96:5000/debiain:bullseye-mips64le

# 在本地删除镜像
docker image rm 192.168.41.96:5000/debiain:bullseye-mips64le
docker image rm debian:bullseye

# 同以上步骤操作linux/arm64与linux/amd64架构镜像。
```

此时私有registry中已经有三种架构的debian镜像，可通过registry API查看

```shell
# 查看registry中都有哪些镜像
curl http://192.168.41.96:5000/v2/_catalog

# 查看registry中debian镜像的版本有哪些
curl http://192.168.41.96:5000/v2/debian/tags/list
```

通过docker manifest命令，把三种架构的debian镜像合并到同一个index中。

使用docker manifest之前，先完成以下准备工作：

1. manifest为docker experimental功能，需要在`/root/.docker/config.json`中配置experimental为"enabled"，手动开启。

    ```json
    {
        "experimental": "enabled"
    }
    ```

2. 在`/etc/docker/daemon.json`中配置experimental为`true`，配置内网registry地址。

    ```json
    {
        "experimental": true,
        "insecure-registries": ["192.168.41.96:5000"]
    }
    ```

3. 关闭docker buildx的attestations选项。

    ```shell

    export BUILDX_NO_ATTESTATION=1
    ```

重启docker`systemctl restart docker`后，合并三种架构镜像的manifest，并推送到私有registry。

```shell
# registry镜像仓库未配置HTTPS，所以访问时需要加上`--insecure`

# 合并manifest
docker manifest create --insecure 192.168.41.96:5000/debian:bullseye-multiv1 192.168.41.96:5000/debiain:bullseye-amd64 192.168.41.96:5000/debiain:bullseye-arm64 192.168.41.96:5000/debiain:bullseye-mips64le

# 推送manifest。
# 推送时会遇到docker HTTPS客户端不能接收registry HTTP response的问题。后来下载了docker 20版本，用docker20中的docker二进制可执行文件执行如下命令没有问题，怀疑是当前环境19.03 docker客户端不支持。其他命令用19.03 docker执行不报错，所以这条命令暂且用20 docker执行。
docker manifest push --insecure 192.168.41.96:5000/debian:bullseye-multiv1

# 查看镜像的manifest
docker manifest inspect --insecure 192.168.41.96:5000/debian:bullseye-multiv1
```

此时，可以在不同架构的主机上拉取debian镜像，验证是否拉取的为本机架构的镜像。

```shell
# 拉取镜像
docker pull 192.168.41.96:5000/debian:bullseye-multiv1

# 查看镜像信息
docker image inspect 192.168.41.96:5000/debian:bullseye-multiv1
```

## 3. 基于debian构建JDK8多架构镜像

我们的java服务基于JDK8开发，需要在debian中安装JDK8，以便运行java服务。

本次构建多架构镜像选用**docker buildx**方案，详见docker官方文档。

docker buildx可以在一台主机上使用qemu模拟来构建非本机架构的镜像，此功能需要Linux内核版本>=4.8，docker版本>=19.03。内网中当前使用的linux/arm64的主机内核为4.19，docker版本为19.03，满足要求。

### 3.1 docker buildx安装

内网主机使用的二进制方式安装的docker，未包含buildx客户端插件，需自行安装。桌面版Docker-Desktop安装时会包含此插件。

从GitHub下载buildx二进制可执行文件`buildx-v0.14.0.linux-arm64`，拷入内网。

```shell
# 修改文件名为docker-buildx
mv buildx-v0.14.0.linux-arm64 docker-buildx

# 创建cli-plugins文件夹
mkdir -p /root/.docker/cli-plugins

# 把docker-build放入cli-plugins中
mv docker-buildx /root/.docker/cli-plugins

# 验证docker buildx安装是否成功
docker buildx --help
```

### 3.2 开启qemu内核支持

需要拉取tonistiigi/binfmt镜像，通过这个镜像开启内核特性以支持多架构构建。

```shell
# 在公网环境拉取镜像
docker pull tonistiigi/binfmt:latest

# 保存镜像为tar文件，拷入内网
docker save -o binfmt.tar tonistiigi/binfmt:latest

# 在内网load镜像
docker load -i binfmt.tar

# 运行镜像开启内核支持
docker run --privileged --rm tonistiigi/binfmt --install all
```

### 3.3 使用buildx构建多架构镜像

docker buildx命令执行时调用的后端为`moby/buildkit`容器服务，因此也需要先把镜像导入内网。

```shell
# 拉取镜像。省略save和load步骤。
docker pull moby/buildkit:buildx-stable-1
```

执行以下步骤创建多架构镜像。

1. 准备JDK8安装包与Dockerfile

    从官网下载所需三种架构的JDK8压缩包，分别解压至当前目录，更改文件夹名字为jdk8-arm64,jdk8-amd64,jdk8-mips64le，示例如下。

    ```shell
    # 解压
    tar xvf jdk-8u401-linux-x64.tar.gz

    # 重命名
    mv jdk1.8.0_401_amd64 jdk8-amd64
    ```

    Dockerfile内容如下:

    ```Dockerfile
    FROM --platform=$TARGETPLATFORM 192.168.41.96:5000/debian:bullseye-multiv1 
    ARG TARGETARCH
    WORKDIR /opt
    ADD jdk8-${TARGETARCH} ./jdk
    ENV JAVA_HOME /opt/jdk
    ENV PATH $PATH:$JAVA_HOME/bin:$JAVA_HOME/jre/bin
    ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$JAVA_HOME/bin:$JAVA_HOME/jre/bin
    ```

    其中TARGETPLATFORM可以从命令行获取到如linux/amd64,TARGETARCH相应的为amd64，以便不同架构镜像读取不同文件夹。通过变量的使用可以提高Dockerfile的灵活性。

2. 创建builder并构建镜像

    ```shell

    docker buildx create --name=multi-arch-builder --driver docker-container --driver-opt image=moby/buildkit:buildx-stable-1 --bootstrap --use --buildkitd-config ./buildkitd.toml
    ```

    其中buildkitd.toml中需要配置私有仓库，否则在push镜像时会报HTTPS的错误，其内容如下。

    ```yaml
    [registry."192.168.41.96::5000"]
        mirrors = ["192.168.41.3:5000"]
        http = true
        insecure = true
    ```

    ```shell
    # 查看当前builder列表
    docker buildx ls

    # 查看builder详情
    docker buildx inspect multi-arch-builder
    ```

    使用builder构建多架构镜像

    ```shell
    # build镜像并推送
    docker buildx build -t 192.168.41.96:5000/debian-jdk8-multi:v1 --platform linux/arm64,linux/amd64,linux/mips64le --push -f Dockerfile .
    ```

    此时通过`docker manifest inspect`命令即可查看镜像仓库中的`debian-jdk8-multi:v1`镜像，发现其已支持多架构。

## 4. 构建java服务镜像

安装好JDK环境的debian镜像我们已经制作完毕，接下来就可以构建java服务镜像了。
Dockerfile内容如下：

```Dockerfile
FROM --platform=$TARGETPLATFORM 192.168.41.96:5000/debian-jdk8-multi:v1
```

构建镜像命令如下：
```shell
docker buildx build -t 192.168.41.96:5000/java-app:v1 --platform linux/arm64,linux/amd64,linux/mips64le --push -f Dockerfile .
```

至此，java服务镜像的构建工作就完成了。可以在不同架构的主机上拉取java服务镜像，验证是否拉取的为本机架构的镜像，然后run镜像即可。


## 参考链接
* [多架构镜像](https://www.zhaowenyu.com/docker-doc/best-practices/mult-arch-image.html)
