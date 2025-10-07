import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("/media/ben/Extreme SSD/particles_ML/2025-10-06_19-06-08/link_sweep_results.csv")

plt.figure(figsize=(8,5))
for mem in sorted(df.memory.unique()):
    subset = df[df.memory==mem]
    plt.plot(subset.search_range, subset.mean_len, '-o', label=f'memory={mem}')
plt.xlabel("Search range (pixels)")
plt.ylabel("Mean track length")
plt.legend()
plt.grid(True)
plt.show()
