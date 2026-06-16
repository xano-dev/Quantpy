from floating_indexes import FloatingIndex

FixingLags = {idx: 2 if "_" in idx.value else 0 for idx in FloatingIndex}
