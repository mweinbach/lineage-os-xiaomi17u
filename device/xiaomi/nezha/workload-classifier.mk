# Exact factory candidate remains blocked until its reviewed closure gates close.
# The baseline adds no package, permission, property, policy or copied file.
NEZHA_WORKLOAD_CLASSIFIER ?= false
ifneq ("$(NEZHA_WORKLOAD_CLASSIFIER)","$(strip $(NEZHA_WORKLOAD_CLASSIFIER))")
$(error NEZHA_WORKLOAD_CLASSIFIER must be exactly true or false)
endif
ifneq ($(words $(NEZHA_WORKLOAD_CLASSIFIER)),1)
$(error NEZHA_WORKLOAD_CLASSIFIER must be exactly true or false)
endif
ifeq ($(filter true false,$(NEZHA_WORKLOAD_CLASSIFIER)),)
$(error NEZHA_WORKLOAD_CLASSIFIER must be exactly true or false)
endif
ifeq ($(NEZHA_WORKLOAD_CLASSIFIER),true)
$(error Nezha workload classifier blocked: signer/domain, hidden API/perf JNI, libtflite ABI, permissions, broadcast boundary and device gates remain open)
endif
