queue = ["job-101", "job-102"]

while True:
    current_job = queue.pop(0)
    print(f"Processing {current_job}")
