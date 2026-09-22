# KDE Tier 2 Package Batch 5

Status: **active — KMime clean build pending**

Batch 5 contains exactly **KMime** from KDE Frameworks 6.30.0. Canonical Tier 2 is **14 PASS / 1 pending / 0 current FAIL / 0 BLOCKED**.

The authoritative package is `kf6-kmime 6.30.0-0supralinux1`, producing `libkf6mime-data`, `libkf6mime-dev` and `libkf6mime6`. Its development/runtime contract is `KF6Mime` / `KF6::Mime` / `libKF6Mime.so.6`. KCodecs 6.30 is the only retained KDE predecessor.

Batch 5 uses the deterministic materialization PASS from run `35684824744`, artifact `10675444852`. A real package attempt begins immediately before `sbuild`; failures before that point are INFRA, not KMime FAIL.

PASS requires the standard clean-build gates plus the ADR-0002 compatibility gates. The built KF6Mime packages must not claim legacy `libkpim6mime6`, `libkmime-dev` or `libkmime-data` through fake `Provides`, `Replaces` or `Breaks`. After installing the built Frameworks packages, CI must install Ubuntu's legacy runtime `libkpim6mime6` + `libkmime-data` on demand and prove that both `libKF6Mime.so.6` and `libKPim6Mime.so.6` remain installed with a clean APT dependency state. The legacy development package is not installed by this runtime compatibility gate.

A Batch 5 PASS makes KMime downstream-eligible and eligible for the SupraLINUX **testing** repository only. Promotion to **stable** always requires explicit user approval.
