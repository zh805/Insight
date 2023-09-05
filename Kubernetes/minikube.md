### minikube

minikube[官方文档](https://minikube.sigs.k8s.io/docs/)

在centos7上安装minikube
```shell
# 先安装docker
sudo yum update
sudo yum install yum-utils device-mapper-persistent-data lvm2
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce
sudo systemctl start docker
sudo systemctl enable docker
# 在非root用户中执行
sudo usermod -aG docker $USER && newgrp docker

# 下载对应平台的minikube并安装
# https://minikube.sigs.k8s.io/docs/start/#:~:text=To%20install%20the%20latest%20minikube%20stable%20release%20on,Make%20sure%20to%20run%20PowerShell%20as%20Administrator.%20
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-latest.x86_64.rpm
sudo rpm -Uvh minikube-latest.x86_64.rpm
```

启动minikube
```shell
# 设置driver为docker
minikube config set driver docker
# 查看已有配置
nikikube config view

# 启动时设置cni为flannel或calico
minikube start --cni=flannel
minikube start --cni=calico

# 添加如下命令到 /home/$USER/.bashrc
echo "alias kubectl=\"minikube kubectl --\"" >> /home/centos/.bashrc

# 测试是否启动
kubectl get nodes -A
```
