import time
from testcort

scripts = [
    (script1, ["Journal1", "https://url1"]),
    (script2, ["Journal2", "https://url2"]),
    (script3, ["Journal3", "https://url3"]),
    #...
]

for script, args in scripts:
    script.main(*args)
    time.sleep(300)  # Sleep for 5 minutes

