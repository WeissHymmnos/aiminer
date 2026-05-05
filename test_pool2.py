import multiprocessing, time, random, os, sys, traceback
multiprocessing.set_start_method("spawn", force=True)

from concurrent.futures import ProcessPoolExecutor, as_completed

def worker(kwargs):
    import faulthandler
    faulthandler.enable()
    try:
        time.sleep(random.uniform(0.1, 1.0))
        from sub_agent import AlphaResearcher
        agent = AlphaResearcher(**kwargs)
        return agent.run()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()}

# Build kwargs similar to manager
from core.settings import build_settings
settings = build_settings(
    evaluation_mode="ricequant",
    evaluation_engine="polars",
    data_backend="local",
    llm_provider="mimo",
    llm_model="Mimo-v2.5",
    embedding_provider="glm",
    market_start="2015-01-01",
    market_end="2020-12-01",
    roles=["动量专家", "波动率专家"],
    max_iterations=1,
    parallel=True,
    swarm_global_timeout_seconds=2000,
)

roles = ["动量专家", "波动率专家"]
kwargs_list = []
for role in roles:
    kw = settings.to_subagent_kwargs(role)
    kw["iteration"] = 1
    kwargs_list.append(kw)

print(f"Submitting {len(kwargs_list)} tasks...")
with ProcessPoolExecutor(max_workers=2) as ex:
    futs = {ex.submit(worker, kw): kw["role_prompt"] for kw in kwargs_list}
    for f in as_completed(futs):
        role = futs[f]
        try:
            r = f.result(timeout=120)
            if isinstance(r, dict) and "error" in r:
                print(f"FAIL {role}: {r['error']}")
                print(r.get("trace", ""))
            else:
                print(f"OK {role}")
        except Exception as e:
            print(f"EXC {role}: {type(e).__name__}: {e}")
print("done")
