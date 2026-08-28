# Authorized execution notes

Brian approved the exact smoke and subsequently authorized using the supplied credential file. It arrived as .env.txt. The file was renamed to .env.runpod.local in the same campaign folder, under the existing Git ignore rule; its contents were never displayed or uploaded. No other credential source is read.

The local controller is operational plumbing, not a replacement for any of the 65 approved source files. It sends exactly those files as a compressed source archive in the pod creation command environment and verifies every target hash before installation. The bootstrap command uses only the Python standard library and opens no public service or port. Evidence returns through the authenticated Runpod v2 container-log API. Account credentials remain local.

A separate hidden local watchdog is armed before pod creation. The controller has an 18-minute deadline, leaving two minutes before the approved 20-minute lifetime cap for deletion and verification; boot plus install is limited to five minutes, tests to two, and study to five. A lost creation response is never retried: recovery matches the unique campaign pod name, and the watchdog stays armed if creation is uncertain.

The live CPU3C quote is $0.06/hour for 2 vCPU and 4 GB RAM. The request specifies 10 GB container disk, zero persistent volume, no GPU, and a $0.002/hour conservative storage reserve. This is below the approved $0.20/hour compute and $0.10 total caps. The approved Python tag was resolved to its Linux amd64 digest before execution; see IMAGE-RESOLUTION.json. No broader study is authorized.
