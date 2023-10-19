### journalctl
```shell
# 查看neutron-server 日志
journalctl -u neutron-server -f
```

### ntpdate
```shell
# 同步服务器时间
sudo ntpdate -u ntp1.aliyun.com
```

### rsync
```shell
# 同步文件夹（排除logs目录）到远程服务器
rsync -av --exclude=logs  -e ssh f5-oslbaasv2-tools  root@10.250.15.160:/root/zhanghui
```

### screen
```shell
#创建名为test1的虚拟终端 
screen -R  test1 

#虚拟终端中开启任务后退出： Ctl+a 然后按 d 

#查看虚拟终端列表 
screen -ls 

#进入虚拟终端 
screen -r test1 
```
