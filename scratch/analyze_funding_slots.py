import csv

def analyze_funding_slots():
    file_path = "scratch/resolved_tokens_batch12.csv"
    
    hyper_clean = ["5LV4xvdkCBXCwAq9ehmhBkhwtFMjgq8XFdWxhWv3pump",
                   "DMRvAber8hUYJFDZWqMoXjjRNDasU1c5cPYtmt7N4LS6",
                   "J1wYDggzvB8Mj7dynpzhHuxk6pqDvPyfouuLzAbnnfe9",
                   "83GeM2UqCJFAa86tcyYacDB9TgaD1vra4vHunuXjpWjq",
                   "CXoJFn8PQYfFbq1Svz8hYjhniwvbD1MfPckzb8VNMMHT"]
                   
    print("Funding Slots for Hyper-Clean Sample:")
    
    # We will also count frequency of funding slots across ALL rugs in batch 12
    funding_slot_counts = {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slot_str = row.get("creator_funding_slot", "")
            if not slot_str or slot_str == "0":
                continue
            
            try:
                slot = int(slot_str)
            except ValueError:
                continue
                
            if row["token_address"] in hyper_clean:
                print(f"Token: {row['symbol']:<8} Address: {row['token_address']} -> Funding Slot: {slot}")
                
            if row["outcome_label"] == "rug":
                funding_slot_counts[slot] = funding_slot_counts.get(slot, 0) + 1
                
    # Print the top clustered funding slots for rugs
    print("\nTop Funding Slot Clusters (Rugs in Batch 12):")
    sorted_slots = sorted(funding_slot_counts.items(), key=lambda x: x[1], reverse=True)
    for slot, count in sorted_slots[:10]:
        if count > 1:
            print(f"Slot {slot}: {count} rugs")

if __name__ == "__main__":
    analyze_funding_slots()
