import re


def compute_averages(filename):
    actual_moves = []
    total_times = []

    # Regex patterns to capture the floats
    re_actual = re.compile(r"Actual move:\s*([0-9]*\.?[0-9]+)")
    re_total = re.compile(r"Total \(time\):\s*([0-9]*\.?[0-9]+)")

    with open(filename, "r") as f:
        for line in f:
            m1 = re_actual.search(line)
            if m1:
                actual_moves.append(float(m1.group(1)))
                continue

            m2 = re_total.search(line)
            if m2:
                total_times.append(float(m2.group(1)))

    if not actual_moves or not total_times:
        print("No matching lines found.")
        return

    avg_actual = sum(actual_moves) / len(actual_moves)
    avg_total = sum(total_times) / len(total_times)

    print(f"Average Actual move time: {avg_actual:.3f} s")
    print(f"Average Total time:       {avg_total:.3f} s")


if __name__ == "__main__":
    compute_averages("./datas/timing.txt")
