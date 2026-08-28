PYTHON ?= python3
SOURCE_DIR ?= $(CURDIR)/sources/evolution
JOBS ?= 8

.DEFAULT_GOAL := help
.PHONY: help doctor refs verify test init sync source-plan linux-packages stock-plan
.PHONY: apple-setup apple-doctor apple-smoke apple-init apple-sync apple-sync-bg apple-status apple-shell apple-plan
.PHONY: twrp-plan recovery-logs-plan

help:
	@printf '%s\n' \
	  'make refs            Fetch pinned upstream references (safe on macOS)' \
	  'make verify          Verify every reference revision and clean worktree' \
	  'make doctor          Report build-host prerequisites' \
	  'make test            Run offline workspace tests' \
	  'make source-plan     Preview full platform init/sync commands' \
	  'make apple-status    Inspect this Mac Apple Container source task' \
	  'make apple-setup     Build/test the Apple Container + Rosetta environment' \
	  'make apple-init      Initialize Evolution X in persistent Linux storage' \
	  'make apple-sync-bg   Start a named background source sync in that VM' \
	  'make apple-shell     Open the source-volume shell when no task is active' \
	  'make linux-packages  Print Ubuntu 24.04 build dependencies' \
	  'make init            Initialize full platform (Linux x86-64 only)' \
	  'make sync JOBS=8     Sync full platform and save resolved manifest' \
	  'make stock-plan      Preview read-only Xiaomi evidence commands' \
	  'make twrp-plan       Preview isolated TWRP source and build commands' \
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

source-plan:
	$(PYTHON) scripts/workspace.py init --source-dir "$(SOURCE_DIR)" --dry-run
	$(PYTHON) scripts/workspace.py sync --source-dir "$(SOURCE_DIR)" --jobs "$(JOBS)" --dry-run

linux-packages:
	bash scripts/setup-linux.sh --print

init:
	$(PYTHON) scripts/workspace.py init --source-dir "$(SOURCE_DIR)"

sync:
	$(PYTHON) scripts/workspace.py sync --source-dir "$(SOURCE_DIR)" --jobs "$(JOBS)"

stock-plan:
	$(PYTHON) scripts/collect_stock.py --serial PREVIEW --expected-device nezha --dry-run

twrp-plan:
	$(PYTHON) scripts/twrp_workspace.py plan
	$(PYTHON) scripts/twrp_build.py plan

recovery-logs-plan:
	$(PYTHON) scripts/collect_recovery.py

apple-setup:
	$(PYTHON) scripts/apple_container.py setup

apple-doctor:
	$(PYTHON) scripts/apple_container.py doctor

apple-smoke:
	$(PYTHON) scripts/apple_container.py smoke

apple-init:
	$(PYTHON) scripts/apple_container.py init

apple-sync:
	$(PYTHON) scripts/apple_container.py sync --jobs "$(JOBS)"

apple-sync-bg:
	$(PYTHON) scripts/apple_container.py sync --jobs "$(JOBS)" --detach

apple-status:
	$(PYTHON) scripts/apple_container.py status

apple-shell:
	$(PYTHON) scripts/apple_container.py shell

apple-plan:
	$(PYTHON) scripts/apple_container.py setup --dry-run
	$(PYTHON) scripts/apple_container.py init --dry-run
	$(PYTHON) scripts/apple_container.py sync --jobs "$(JOBS)" --detach --dry-run
