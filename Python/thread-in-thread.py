import threading


class Thread1(threading.Thread):
    def run(self) -> None:
        print('I am thread 1')


class Thread2(threading.Thread):
    def run(self) -> None:
        print('I am thread 2')
        t1 = Thread1()
        t1.start()



if __name__ == '__main__':
    t2 = Thread2()
    t2.start()


