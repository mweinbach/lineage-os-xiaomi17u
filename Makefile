PYTHON ?= python3
SOURCE_DIR ?= $(CURDIR)/sources/evolution
SOURCE_LOCK ?= config/evolution-source-lock.json
JOBS ?= 8
RECOVERY_LOCAL_CONFIG ?= $(CURDIR)/.tools/recovery-local.json
RECOVERY_OUTPUT ?= $(CURDIR)/artifacts/twrp/nezha/builds/$(shell date -u +%Y%m%dT%H%M%SZ)
RECOVERY_IMAGE ?=
RECOVERY_BUNDLE ?= $(SOURCE_DIR)/vendor/xiaomi/nezha-recovery
RECOVERY_COMPOSED_SOURCE_CONTRACT ?=
RECOVERY_COMPOSED_SOURCE_ARGS = $(if $(strip $(RECOVERY_COMPOSED_SOURCE_CONTRACT)),--composed-source-contract "$(RECOVERY_COMPOSED_SOURCE_CONTRACT)")
SOURCE_LOCK_ARGS = $(if $(strip $(SOURCE_LOCK)),--source-lock "$(SOURCE_LOCK)")

# The fast iteration suite for the Package7 baseline. Full discovery remains
# the completion gate; update this selection when the active build path changes.
CURRENT_TEST_MODULES = \
	test_source_lock \
	test_twrp_working_defaults test_twrp_working test_recovery_inputs \
	test_factory_boot_build test_boot_dlkm_build \
	test_avb_signing test_avb_image_set \
	test_sparse_images test_logical_partitions \
	test_target_files_delivery test_target_files_archive_copy \
	test_reconcile_signed_target_files \
	test_familyspace_privapp_permissions test_signapk_stored_entry_timestamps \
	test_experimental_flash_bundle test_device_flash_preflight \
	test_collect_stock test_collect_recovery \
	test_hardware_qualification test_ims_inputs test_ims_telephony_api \
	test_power_inputs test_display_panel_inputs \
	test_dolby_inputs test_dolby_controller test_haptics_controls \
	test_camera_task_profiles test_refresh_policy test_workload_classifier_inputs \
	test_collect_performance test_performance_analysis

.DEFAULT_GOAL := help
.PHONY: help doctor refs verify test test-current init sync source-plan source-check linux-packages stock-plan
.PHONY: apple-setup apple-doctor apple-smoke apple-init apple-sync apple-sync-bg apple-status apple-shell apple-plan
.PHONY: twrp-plan twrp-source-plan recovery-plan recovery-build recovery-verify recovery-stage recovery-inputs-verify recovery-logs-plan
.PHONY: feature-diagnostics-plan hardware-qualification-plan
.PHONY: performance-plan refresh-policy-verify

help:
	@printf '%s\n' \
	  'make refs            Fetch pinned upstream references (safe on macOS)' \
	  'make verify          Verify every reference revision and clean worktree' \
	  'make doctor          Report build-host prerequisites' \
	  'make test-current    Run focused offline checks for Package7 iteration' \
	  'make test            Run all offline workspace tests (completion gate)' \
	  'make source-plan     Preview full platform init/sync commands' \
	  'make source-check    Audit an existing platform against the reviewed source lock' \
	  'make apple-status    Inspect this Mac Apple Container source task' \
	  'make apple-setup     Build/test the Apple Container + Rosetta environment' \
	  'make apple-init      Initialize Evolution X in persistent Linux storage' \
	  'make apple-sync-bg   Start a named background source sync in that VM' \
	  'make apple-shell     Open the source-volume shell when no task is active' \
	  'make linux-packages  Print Ubuntu 24.04 build dependencies' \
	  'make init            Initialize full platform (Linux x86-64 only)' \
	  'make sync JOBS=8     Sync full platform and save resolved manifest' \
	  'make stock-plan      Preview read-only Xiaomi evidence commands' \
	  'make feature-diagnostics-plan Preview extended feature observations without a phone' \
	  'make hardware-qualification-plan Print the measured hardware acceptance checklist' \
	  'make performance-plan Preview bounded read-only performance snapshots; no phone access' \
	  'make refresh-policy-verify Verify the guarded refresh source resources offline' \
	  'make recovery-plan   Preview the working TWRP build and ROM input contract' \
	  'make recovery-build  Reproduce working76 using ignored local input/tool/key paths' \
	  'make recovery-verify RECOVERY_IMAGE=... Verify the exact image and AVB signature' \
	  'make recovery-stage SOURCE_DIR=... RECOVERY_IMAGE=... Stage the private ROM recovery bundle' \
	  'make recovery-inputs-verify SOURCE_DIR=... Verify the staged ROM recovery bundle' \
	  'make twrp-plan       Alias for the current recovery plan' \
	  'make twrp-source-plan Preview the preserved TWRP source experiment' \
	  'make recovery-logs-plan Preview bounded recovery diagnostics; no phone access'

doctor:
	$(PYTHON) scripts/workspace.py doctor --source-dir "$(SOURCE_DIR)"

refs:
	$(PYTHON) scripts/workspace.py fetch

verify:
	$(PYTHON) scripts/workspace.py verify

test:
	$(PYTHON) -m unittest discover -s tests -v
	bash -n scripts/setup-linux.sh

test-current:
	PYTHONPATH="$(CURDIR)/tests:$(CURDIR)" $(PYTHON) -m unittest -v $(CURRENT_TEST_MODULES)

performance-plan:
	$(PYTHON) scripts/collect_performance.py --serial EXPLICIT_AUTHORIZED_SERIAL --expected-device nezha --output artifacts/performance/preview --dry-run

refresh-policy-verify:
	$(PYTHON) scripts/refresh_policy.py verify-source

source-plan:
	$(PYTHON) scripts/workspace.py init --source-dir "$(SOURCE_DIR)" $(SOURCE_LOCK_ARGS) --dry-run
	$(PYTHON) scripts/workspace.py sync --source-dir "$(SOURCE_DIR)" --jobs "$(JOBS)" $(SOURCE_LOCK_ARGS) --dry-run

source-check:
	$(if $(strip $(SOURCE_LOCK)),,$(error Set SOURCE_LOCK to the reviewed source-lock descriptor))
	$(PYTHON) scripts/workspace.py check-source --source-dir "$(SOURCE_DIR)" --source-lock "$(SOURCE_LOCK)"

linux-packages:
	bash scripts/setup-linux.sh --print

init:
	$(PYTHON) scripts/workspace.py init --source-dir "$(SOURCE_DIR)" $(SOURCE_LOCK_ARGS)

sync:
	$(PYTHON) scripts/workspace.py sync --source-dir "$(SOURCE_DIR)" --jobs "$(JOBS)" $(SOURCE_LOCK_ARGS)

stock-plan:
	$(PYTHON) scripts/collect_stock.py --serial PREVIEW --expected-device nezha --dry-run

feature-diagnostics-plan:
	$(PYTHON) scripts/collect_stock.py --serial PREVIEW --expected-device nezha --feature-diagnostics --dry-run

hardware-qualification-plan:
	$(PYTHON) scripts/hardware_qualification.py plan

twrp-plan: recovery-plan

twrp-source-plan:
	$(PYTHON) scripts/twrp_workspace.py plan
	$(PYTHON) scripts/twrp_build.py plan

recovery-plan:
	$(PYTHON) scripts/twrp_working.py plan
	$(PYTHON) scripts/recovery_inputs.py plan $(RECOVERY_COMPOSED_SOURCE_ARGS)

recovery-build:
	$(PYTHON) scripts/twrp_working.py build --local-config "$(RECOVERY_LOCAL_CONFIG)" --output-dir "$(RECOVERY_OUTPUT)"

recovery-verify:
	$(if $(strip $(RECOVERY_IMAGE)),,$(error Set RECOVERY_IMAGE to the image to verify))
	$(PYTHON) scripts/twrp_working.py verify --local-config "$(RECOVERY_LOCAL_CONFIG)" --image "$(RECOVERY_IMAGE)"

recovery-stage:
	$(if $(strip $(RECOVERY_IMAGE)),,$(error Set RECOVERY_IMAGE to the verified image to stage))
	$(PYTHON) scripts/recovery_inputs.py stage --local-config "$(RECOVERY_LOCAL_CONFIG)" --source-tree "$(SOURCE_DIR)" --image "$(RECOVERY_IMAGE)" --output-dir "$(RECOVERY_BUNDLE)" $(RECOVERY_COMPOSED_SOURCE_ARGS)

recovery-inputs-verify:
	$(PYTHON) scripts/recovery_inputs.py verify --local-config "$(RECOVERY_LOCAL_CONFIG)" --source-tree "$(SOURCE_DIR)" --bundle "$(RECOVERY_BUNDLE)" $(RECOVERY_COMPOSED_SOURCE_ARGS)

recovery-logs-plan:
	$(PYTHON) scripts/collect_recovery.py

apple-setup:
	$(PYTHON) scripts/apple_container.py setup

apple-doctor:
	$(PYTHON) scripts/apple_container.py doctor

apple-smoke:
	$(PYTHON) scripts/apple_container.py smoke

apple-init:
	$(PYTHON) scripts/apple_container.py init $(SOURCE_LOCK_ARGS)

apple-sync:
	$(PYTHON) scripts/apple_container.py sync --jobs "$(JOBS)" $(SOURCE_LOCK_ARGS)

apple-sync-bg:
	$(PYTHON) scripts/apple_container.py sync --jobs "$(JOBS)" --detach $(SOURCE_LOCK_ARGS)

apple-status:
	$(PYTHON) scripts/apple_container.py status

apple-shell:
	$(PYTHON) scripts/apple_container.py shell

apple-plan:
	$(PYTHON) scripts/apple_container.py setup --dry-run
	$(PYTHON) scripts/apple_container.py init $(SOURCE_LOCK_ARGS) --dry-run
	$(PYTHON) scripts/apple_container.py sync --jobs "$(JOBS)" --detach $(SOURCE_LOCK_ARGS) --dry-run
