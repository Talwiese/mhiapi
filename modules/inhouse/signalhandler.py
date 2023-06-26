
import signal

class SignalHandler: 
    def __init__(self):
        self.interrupt = False
        self.terminate = False
        signal.signal(signal.SIGINT, self.on_interrupt)
        signal.signal(signal.SIGTERM, self.on_terminate)
    def on_interrupt(self, *args):
        self.interrupt = True
        #log.info("Process terminates due to received SIGINT.")
    def on_terminate(self, *args):
        #log.info("Process terminates due to received SIGTERM.")
        self.terminate = True 
