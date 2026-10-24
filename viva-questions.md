# College Viva & Technical Interview Questions (Q&A)

This guide provides answers to common questions asked during college evaluations, project vivas, and technical interviews regarding this Bloom Filter project.

---

### Q1: What is a Bloom Filter, and why is it called a "probabilistic" data structure?
**Answer:**  
A Bloom Filter is a space-efficient data structure created by Burton Bloom in 1970 to test set membership ($x \in S$).  
It is called **probabilistic** because its answers are not deterministic when it says "yes":
- When it returns **False**, it is **$100\%$ certain** that the item is NOT present (Zero False Negatives).
- When it returns **True**, the item **might** be present, but there is a small, bounded probability that it is a **False Positive**.

---

### Q2: Why is a False Negative impossible in a standard Bloom Filter?
**Answer:**  
When an element is added, all $k$ bit positions calculated by the hash functions are set to `1`. In a standard Bloom Filter, bits are **never flipped back to 0**.  
When querying that same element, the algorithm checks the exact same $k$ bit positions. Since all of them were set to `1` and none were cleared, all checked positions will still be `1`.  
Because the query returns `False` *only if at least one bit is 0*, an added item can never return `False`.

---

### Q3: What causes a False Positive?
**Answer:**  
A false positive occurs due to **hash collision overlap across multiple elements**.  
Suppose item $A$ set bits $\{2, 5\}$, item $B$ set bits $\{5, 9\}$, and item $C$ set bits $\{12, 18\}$. If an unseen item $X$ hashes to bits $\{2, 9\}$, both bits are already `1` even though $X$ was never added. The filter will erroneously report that $X$ is present.

---

### Q4: Can you delete an element from a standard Bloom Filter?
**Answer:**  
**No.** In a standard Bloom Filter, multiple elements share the same bit positions. If you flip a bit from `1` to `0` to delete one item, you might inadvertently unset bits that belong to other inserted items, introducing **false negatives** and breaking the fundamental guarantee.  
*(Note: To support deletions, you would use a **Counting Bloom Filter**, which stores small integer counters instead of single bits, at the cost of 3–4x more memory).*

---

### Q5: How do you choose the optimal size of the bit array ($m$) and number of hash functions ($k$)?
**Answer:**  
Using the standard mathematical formulas:
$$m = -\frac{n \cdot \ln(p)}{(\ln 2)^2} \approx -2.08136 \cdot n \cdot \ln(p)$$
$$k = \frac{m}{n} \cdot \ln(2)$$
Where $n$ is the expected number of elements and $p$ is the acceptable false-positive probability.

---

### Q6: What is the Kirsch-Mitzenmacher optimization?
**Answer:**  
Instead of running $k$ separate cryptographic hash functions (which is slow), Adam Kirsch and Michael Mitzenmacher proved that **two independent hash values** ($h_1$ and $h_2$) are sufficient to produce $k$ pseudo-independent hash positions using the linear combination:
$$g_i(x) = (h_1(x) + i \cdot h_2(x)) \pmod m$$
This maintains identical asymptotic false-positive bounds while operating significantly faster.

---

### Q7: What are the Time and Space Complexities?
**Answer:**
- **Time Complexity:**
  - `add(x)`: $\mathcal{O}(k)$ time to hash and set $k$ bits.
  - `might_contain(x)`: $\mathcal{O}(k)$ time to check $k$ bits (with short-circuiting on the first 0).
  - Since $k$ is constant (typically 4 to 10), operations run in $\mathcal{O}(1)$ nanosecond time.
- **Space Complexity:** $\mathcal{O}(m)$ bits, completely independent of the size or length of the inserted strings.

---

### Q8: How does the Bloom Filter save database lookups in your Two-Tier architecture?
**Answer:**  
In high-throughput systems, disk and network database lookups are expensive ($10\text{--}50\text{ ms}$).  
By placing the Bloom Filter in RAM as an **L1 screener**:
- When an event is fresh ($might\_contain == False$), we know with $100\%$ certainty that it is not in the database. We insert it directly and **skip the database lookup entirely**.
- Only when the Bloom Filter returns $True$ do we perform a database lookup to confirm if it is a genuine duplicate or a false positive.
- If $90\%$ of incoming traffic is fresh, the Bloom Filter avoids $90\%$ of expensive database read queries!

---

### Q9: How much memory did your implementation save compared to a standard Python `set`?
**Answer:**  
For $10,000$ events with a $1\%$ target error rate:
- The Bloom Filter uses **$11.76\text{ KB}$** ($95,851\text{ bits}$).
- A Python `set` storing $10,000$ strings in memory requires approximately **$1,140\text{ KB}$ ($1.14\text{ MB}$)**.
- This represents an empirical memory reduction of **$98.9\%$**.
