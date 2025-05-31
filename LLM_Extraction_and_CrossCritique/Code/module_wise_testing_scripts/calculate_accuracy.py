import re
import os

def calculate_accuracy_and_append(file_path: str) -> None:
    """
    Extended accuracy calculator with three outputs:
    
    1. Overall Accuracy
    2. Non-null Gold Accuracy
    3. A new file containing only non-null gold lines:
       "evaluation_results_non_null_only.txt" in the same folder as file_path.
    """
    NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
    value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)

    correct = total = 0
    non_null_correct = non_null_total = 0
    non_null_lines = []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # 1. Overall accuracy logic
        if "Not Equivalent" in line:
            total += 1
        elif "Equivalent" in line:
            total += 1
            correct += 1

        # 2. Non-null evaluation logic
        match = value_pattern.search(line)
        if match:
            gold_val = match.group(1).strip()
            if gold_val.lower() not in NULL_TOKENS:
                non_null_total += 1
                non_null_lines.append(line)
                if "Equivalent" in line and "Not Equivalent" not in line:
                    non_null_correct += 1

    overall_acc = (correct / total * 100) if total else 0.0
    non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total else 0.0

    summary = (
        f"\nTotal Evaluated Lines: {total}\n"
        f"Equivalent Lines: {correct}\n"
        f"Overall Accuracy: {overall_acc:.2f}%\n\n"
        f"Non-null Gold Lines: {non_null_total}\n"
        f"Non-null Correct Lines: {non_null_correct}\n"
        f"Non-null Accuracy: {non_null_acc:.2f}%"
    )

    # Append summary to the original file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(summary)

    # Determine the output path for non-null lines
    output_dir = os.path.dirname(file_path)
    output_path = os.path.join(output_dir, "evaluation_results_non_null_only.txt")

    # Write non-null lines to new file
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(non_null_lines)

if __name__ == "__main__":
    file_path = "db/NCT00268476_James_STAMPEDE_IJC'22/evaluation_results.txt"
    calculate_accuracy_and_append(file_path)