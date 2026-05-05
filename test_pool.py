import faulthandler, signal, sys, os, traceback
faulthandler.enable()

from concurrent.futures import ProcessPoolExecutor, as_completed

def worker(x):
    try:
        faulthandler.enable()
        from sub_agent import AlphaResearcher
        return os.getpid(), 'ok', x
    except Exception as e:
        return os.getpid(), f'{type(e).__name__}: {e}', x

with ProcessPoolExecutor(max_workers=5) as ex:
    futs = [ex.submit(worker, i) for i in range(5)]
    for f in as_completed(futs):
        try:
            print(f.result(timeout=60))
        except Exception as e:
            print(f'Exception: {type(e).__name__}: {e}')
print('done')
