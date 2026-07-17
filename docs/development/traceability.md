# Requirements-to-tests traceability matrix

Maps every requirement in [requirements.md](requirements.md) to the tests that
prove it. Requirements marked **Deferred** carry a target release and are listed
in [ROADMAP.md](https://github.com/demilade-o/convexity/blob/main/ROADMAP.md); none is dropped.

Regenerate the evidence with:

```bash
uv run pytest --cov --cov-branch -q
```

## Conventions

| ID | Proven by |
| --- | --- |
| REQ-CON-001 | `test_conventions.py::TestAnnualisationPrecedence::test_explicit_periods_per_year_wins_over_everything`, `::test_frequency_wins_over_index`, `::test_index_used_only_as_last_resort` |
| REQ-CON-002 | `test_conventions.py::TestAnnualisationPrecedence::test_no_route_raises_and_does_not_assume_252`; `test_performance_sortino.py::TestFrequency::test_no_annualisation_route_raises_rather_than_assuming_252`; `test_returns.py::TestAnnualisedReturn::test_no_annualisation_route_raises` |
| REQ-CON-003 | `test_conventions.py::TestInference::test_recognises_regular_frequencies`, `::test_reports_evidence_not_just_a_verdict` |
| REQ-CON-004 | `test_conventions.py::TestInference::test_irregular_data_has_low_confidence`, `::test_unrecognisable_spacing_returns_none_rather_than_rounding`; `TestAnnualisationPrecedence::test_low_confidence_inference_raises_with_diagnostics` |
| REQ-CON-005 | `test_conventions.py::TestInference::test_business_daily_distinguished_from_calendar_daily` |
| REQ-CON-006 | `test_conventions.py::TestInference::test_resolution_independent`; `TestDayCountArray::test_resolution_independent` |
| REQ-CON-007 | `test_conventions.py::TestCompounding::*` (round trip parametrised over 3 conventions x 4 rates x 4 frequencies); `property/test_invariants.py::TestCompoundingRoundTrips::*` |
| REQ-CON-008 | `test_conventions.py::TestDayCount::*` (ACT/360 and ACT/365F reference examples, leap-day boundary, denominator ratio) |
| REQ-CON-009 | **Deferred → 0.3.0.** Not implemented; absent from `DayCount` rather than approximated. |

## Returns

| ID | Proven by |
| --- | --- |
| REQ-RET-001 | `test_returns.py::TestSimpleReturns::*`, `::TestLogReturns::*` |
| REQ-RET-002 | `test_returns.py::TestWealthIndex::*`, `::TestCumulativeReturn::*`; `property/test_invariants.py::TestWealthAndReturnConsistency::*` |
| REQ-RET-003 | `test_returns.py::TestAnnualisedReturn::test_hand_worked_monthly` (hand derivation) |
| REQ-RET-004 | `test_returns.py::TestArithmeticAnnualisedReturn::*`; `::TestAnnualisedReturn::test_geometric_below_arithmetic_for_volatile_series` |
| REQ-RET-005 | `test_returns.py::TestCagr::*` |
| REQ-RET-006 | `test_returns.py::TestConversions::test_round_trip_simple_to_log_and_back`; `property/test_invariants.py::TestReturnConversionRoundTrips::*` |
| REQ-RET-007 | `test_validation.py::TestValidateReturns::test_percentage_mistake_is_not_second_guessed` |
| REQ-RET-008 | `test_performance_sharpe.py::TestRiskFree::*`; `test_performance_sortino.py::TestScalarTarget::*`, `::TestTimeVaryingTarget::*` |
| REQ-RET-009 | **Deferred → 0.2.0** |
| REQ-RET-010 | **Deferred → 0.5.0** |

## Risk

| ID | Proven by |
| --- | --- |
| REQ-RSK-001 | `test_risk.py::TestVolatility::test_hand_worked_periodic`, `::test_ddof_changes_the_answer` |
| REQ-RSK-002 | `test_risk.py::TestVolatility::test_annualisation_scales_by_sqrt_m`, `::test_annualise_requires_a_frequency_route` |
| REQ-RSK-003 | `test_risk.py::TestDownsideDeviation::*`; `test_performance_sortino.py::TestDownsideConvention::*` (asserts the two conventions differ by exactly `sqrt(12)`) |
| REQ-RSK-004 | `test_risk.py::TestUpsideDeviation::*` |
| REQ-RSK-005 | `test_risk.py::TestDrawdownSeries::*`, `::TestMaxDrawdown::*`; `property/test_invariants.py::TestDrawdownInvariants::*` |
| REQ-RSK-006 | `test_risk.py::TestDrawdownEpisodes::*` (including the unrecovered case reporting `recovery=None`) |
| REQ-RSK-007 | `test_risk.py::TestAverageDrawdown::*` |
| REQ-RSK-008 | `test_risk.py::TestUlcerAndPain::*`; `property/test_invariants.py::TestDrawdownInvariants::test_ulcer_never_below_pain` |
| REQ-RSK-009 | `test_risk.py::TestSkewness::*`, `::TestKurtosis::*` (known values, Fisher/Pearson relation, bias variants, zero-variance → `nan`) |
| REQ-RSK-010 | `test_risk.py::TestTrackingError::*` |
| REQ-RSK-011 | **Deferred → 0.5.0** |

## Ratios

| ID | Proven by |
| --- | --- |
| REQ-RAT-001 | `test_performance_sharpe.py::TestHandWorkedDerivation::*` (hand derivation; numerator exactly 0.15) |
| REQ-RAT-002 | `test_performance_sortino.py::TestHandWorkedDerivation::*` (hand derivation; ratio exactly 8/3) |
| REQ-RAT-003 | `test_performance_calmar.py::TestHandWorkedDerivation::*`, `::TestLookback::*` (including that the lookback excludes an earlier deeper drawdown) |
| REQ-RAT-004 | `test_performance_calmar.py::TestLookback::test_full_sample_by_default` |
| REQ-RAT-005 | `test_performance_sortino.py::TestTimeVaryingTarget::*`; `test_performance_calmar.py::TestRiskFree::*`; `test_performance_sharpe.py::TestRiskFree::*` |
| REQ-RAT-006 | `test_performance_sortino.py::TestRollingWindows::*`; `test_performance_calmar.py::TestRollingCalmar::*`; `test_performance_sharpe.py::TestRollingSharpe::*` |
| REQ-RAT-007 | `TestZeroDenominatorPolicy` in all three ratio test modules (`+inf`, `-inf`, and `nan` cases each asserted) |
| REQ-RAT-008 | `test_registry.py::TestContestedDefinitionsCiteSources::*` |
| REQ-RAT-009 | **Deferred → 0.5.0** |

## Alignment and point-in-time integrity

| ID | Proven by |
| --- | --- |
| REQ-PIT-001 | `test_alignment.py::TestAlignAsof::test_future_observation_never_informs_an_earlier_date`; `test_performance_{sortino,calmar,sharpe}.py::*::test_future_rate_does_not_leak_backwards`; `property/test_invariants.py::TestAlignmentInvariants::test_asof_never_returns_a_future_value` |
| REQ-PIT-002 | `test_alignment.py::TestStaleness::*` |
| REQ-PIT-003 | `test_alignment.py::TestPublicationLag::*` |
| REQ-PIT-004 | `test_alignment.py::TestAlignSeries::test_no_value_is_borrowed_from_a_neighbour` |
| REQ-PIT-005 | `test_alignment.py::TestAlignSeries::test_no_overlap_raises_rather_than_returning_empty` |
| REQ-PIT-006 | `test_alignment.py::TestAlignAsof::test_mixed_datetime_resolutions_align` (4x4 parametrised over every unit pairing) |

## Validation and edge cases

| ID | Proven by |
| --- | --- |
| REQ-VAL-001 | `test_validation.py::TestNaNPolicy::*` |
| REQ-VAL-002 | `test_validation.py::TestValidateDatetimeIndex::*` |
| REQ-VAL-003 | `test_validation.py::TestValidateReturns::test_infinities_always_rejected`, `::TestNaNPolicy::test_infinity_rejected_even_under_propagate` |
| REQ-VAL-004 | `test_validation.py::TestValidateReturns::test_return_below_minus_one_rejected`, `::test_total_loss_allowed_by_default` |
| REQ-VAL-005 | `TestNonMutation` in every metric module; `property/test_invariants.py::TestNonMutation::test_no_metric_mutates_its_input` |
| REQ-VAL-006 | `test_validation.py::TestValidateReturns::test_empty_series_rejected`, `::test_min_observations_enforced`; `test_returns.py::TestSimpleReturns::test_single_price_rejected` |
| REQ-VAL-007 | `test_risk.py::TestVolatility::test_constant_series_has_exactly_zero_volatility`; `test_performance_sharpe.py::TestZeroDenominatorPolicy::*` |
| REQ-VAL-008 | Every `pytest.raises` in the suite asserts a `convexity.exceptions` type and matches on message content |

## Data providers

| ID | Proven by |
| --- | --- |
| REQ-DAT-001 | `lint-imports` forbidden contract (no analytics module may import `httpx`, `socket`, `urllib`, `requests`, `yfinance`); the entire suite runs under `--disable-socket` |
| REQ-DAT-002 | `scripts/check_artefacts.py` (run in CI and the release workflow); `scripts/check_staged.py` (pre-commit); both verified to reject `ref/`, `.env`, `secrets.toml` and `.csv` fixtures while passing ordinary source |
| REQ-DAT-003 … 008 | **Deferred → 0.2.0.** No provider code ships in 0.1.0; the `providers` and `yahoo` extras are declared but empty of adapters. |

## Packaging and quality

| ID | Proven by |
| --- | --- |
| REQ-PKG-001 | `uv build`; `uvx twine check --strict dist/*` |
| REQ-PKG-002 | Clean-venv install and import from wheel and from sdist |
| REQ-PKG-003 | `scripts/check_artefacts.py` asserts `convexity/py.typed` is a wheel member |
| REQ-PKG-004 | `.github/workflows/ci.yml` `test` matrix — **defined; executes on a remote** |
| REQ-PKG-005 | `.github/workflows/ci.yml` `minimum-dependencies` job — **defined; executes on a remote** |
| REQ-PKG-006 | `coverage report --fail-under=95` (core) and `--fail-under=90` (total), both exit 0 |
| REQ-PKG-007 | `ruff format --check`, `ruff check`, `mypy`, `lint-imports` |
| REQ-PKG-008 | `mkdocs build --strict` |
| REQ-PKG-009 | `.github/workflows/security.yml` — **defined; executes on a remote** |
| REQ-PKG-010 | `.github/workflows/release.yml` — **defined; requires owner approval and a remote** |
| REQ-PKG-011 | `test_registry.py::TestRegistryCoversThePublicApi::test_every_exported_metric_is_registered` (34 of 34) |
| REQ-PKG-012 | `test_registry.py::TestSpecCompleteness::*`; hand derivations for Sharpe, Sortino and Calmar; 27 property tests |

## Summary

| Status | Count |
| --- | --- |
| Implemented and locally verified | 47 |
| Implemented; configuration verified, execution requires a remote | 5 |
| Deferred with a target release | 11 |
| **Unimplemented and untracked** | **0** |

No in-scope requirement for 0.1.0 is unimplemented. Every deferred requirement
names its target release.
