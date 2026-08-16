"""Opponent mix inside a corpus, against the current field."""
import collections, sys
import train_gbdt as T

tag = sys.argv[1] if len(sys.argv) > 1 else "n0814"
CTX, QID, Y, X_, OPP = T.load_family(tag, "main", None, None)
c = collections.Counter(OPP)
NAME = {0: "(none)", 1: "mixed_ex3", 2: "mixed_ex1", 3: "mixed_ex4", 4: "dragapult",
        5: "ex_beatdown", 6: "crustle", 7: "lucario", 8: "non_ex", 9: "mixed_ex2"}
FIELD = {"mixed_ex3": 6.1, "mixed_ex1": 12.8, "mixed_ex4": 12.8, "dragapult": 34.2,
         "ex_beatdown": 27.3, "crustle": 2.0, "lucario": 3.1}
tot = sum(c.values())
print(f"{tag}: {tot:,} decisions (teacher WINS only)")
print(f"{'opponent':<14}{'decisions':>12}{'share':>8}{'08-15 field':>13}")
for k, n in c.most_common():
    nm = NAME.get(k, str(k))
    f = FIELD.get(nm)
    print(f"{nm:<14}{n:>12,}{n/tot:>7.1%}{(f'{f}%' if f else '-'):>13}")
