
## Control Groups

cgroup 控制容器可以使用的资源数量

## Namespaces

namespace控制容器内的进程所能看到的内容,用于隔离和虚拟化一系列进程的系统资源

```shell
# 查看1号进程的namespace
ps -p 1 -o pid,pidns
ls -l /proc/1/ns
```

## Setting Up Namespaces

![Root network namespace and container network namespace](images/Root%20network%20namespace%20and%20container%20network%20namespace%20.png)

下面是创建网络命名空间、网桥和 veth 对并将它们连接起来所需的所有 Linux 命令：

```shell
# 查看ip_forward属性
$ sysctl net.ipv4.ip_forward

# 启用数据包端口转发
$ echo 1 > /proc/sys/net/ipv4/ip_forward

# 查看network namespace
$ sudo ip netns list

# 创建net1 netns
$ sudo ip netns add net1

# 创建veth对，以便在root网络命名空间和container网络命名空间net1之间进行通信
$ sudo ip link add veth0 type veth peer name veth1

# 将 veth1 移入之前创建的新网络命名空间
$ sudo ip link set veth1 netns net1
# ip netns exec验证veth1位于网络命名空间 net1 中
$ ip netns exec net1 ip link list

#$ sudo ip link add veth0 type veth peer name veth1

# 为net1的veth1分配ip
$ sudo ip netns exec net1 ip addr add 192.168.1.101/24 dev veth1
# 打开veth1
$ sudo ip netns exec net1 ip link set dev veth1 up

# 创建bridge并连接veth0
$ sudo ip link add br0 type bridge
$ sudo ip link set dev br0 up
$ sudo ip link set enp0s3 master br0
$ sudo ip link set veth0 master br0
$ sudo ip netns exec net1  ip route add default via 192.168.1.100
```
