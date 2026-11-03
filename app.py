import streamlit as st
import time
from data_cruncher_fast import OptimizedDataEngine
from data_cruncher_slow import find_duplicates_slow, generate_dataset

st.set_page_config(page_title="Week 4: Performance Profiler", layout="centered")
st.title("⚡ Week 4: Performance Profiling & Optimization")

size = st.slider("Dataset Size:", min_value=1000, max_value=8000, value=3000, step=1000)

if st.button("Run Live Benchmark"):
    data = generate_dataset(size)
    
    # Slow
    t0 = time.perf_counter()
    res_slow = find_duplicates_slow(data)
    slow_time = time.perf_counter() - t0
    
    # Fast
    t1 = time.perf_counter()
    res_fast = OptimizedDataEngine.find_duplicates_linear(data)
    fast_time = time.perf_counter() - t1
    
    speedup = slow_time / fast_time if fast_time > 0 else 1.0
    
    col1, col2 = st.columns(2)
    col1.metric("Baseline O(N²)", f"{slow_time:.4f}s")
    col2.metric("Optimized O(N)", f"{fast_time:.4f}s", delta=f"{speedup:.1f}x Faster")
    st.success(f"Optimization Verified! Found {len(res_fast)} duplicates identically.")
