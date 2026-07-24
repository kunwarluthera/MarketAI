# Dependency security review

The frontend production build passes in Node 22. The previous npm audit reported advisories in the
development dependency tree; no `npm audit fix --force` was applied. These advisories require a
planned package-by-package upgrade before any non-local deployment. Python dependencies are pinned
by the container build ranges and should receive a supported scanner in the next milestone.
