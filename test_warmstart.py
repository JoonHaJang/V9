from config_mip import mip_config
from nonlinear_mip_optimizer import NonLinearMIPOptimizer

opt = NonLinearMIPOptimizer(mip_config)
print(f"Has warmstart_engine: {hasattr(opt, 'warmstart_engine')}")
print(f"use_warm_start: {opt.use_warm_start}")
print(f"Has enable_warmstart method: {hasattr(opt, 'enable_warmstart')}")
