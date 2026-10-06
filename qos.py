"""Single-process token bucket. Not a distributed rate-limit service."""
import threading
import time


class TokenBucket:
    def __init__(self,capacity=30,refill_per_second=5,clock=time.monotonic):
        if capacity<=0 or refill_per_second<=0:raise ValueError('INVALID_RATE_POLICY')
        self.capacity=capacity;self.refill=refill_per_second;self.tokens=float(capacity)
        self.clock=clock;self.updated=clock();self.lock=threading.Lock()

    def admit(self):
        with self.lock:
            current=self.clock();self.tokens=min(self.capacity,self.tokens+max(0,current-self.updated)*self.refill);self.updated=current
            if self.tokens<1:return False
            self.tokens-=1;return True
