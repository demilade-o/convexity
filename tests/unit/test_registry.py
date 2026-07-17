"""The registry and the public API must not drift apart.

A catalogue maintained by hand is wrong within a release, and a wrong catalogue
is worse than none: users read it to learn which convention produced a number.
These tests make drift a CI failure rather than a discovery.
"""

from __future__ import annotations

import inspect

import pytest

import convexity as cx
from convexity import registry
from convexity.registry import REGISTRY, Category, MetricSpec, Status

# Public names that are deliberately not metrics: types, errors, policies, and
# diagnostics. Everything else exported from the package must be registered.
NON_METRIC_EXPORTS = frozenset(
    {
        "Annualisation",
        "Compounding",
        "DayCount",
        "DownsideConvention",
        "DrawdownEpisode",
        "Frequency",
        "FrequencyInference",
        "NaNPolicy",
        "__version__",
        "show_versions",
        "versions",
    }
)


def _exported_callables() -> set[str]:
    """Public callables in ``convexity.__all__`` that are plain functions."""
    names: set[str] = set()
    for name in cx.__all__:
        if name in NON_METRIC_EXPORTS or name.endswith("Error"):
            continue
        obj = getattr(cx, name)
        if inspect.isclass(obj):
            continue
        if callable(obj):
            names.add(name)
    return names


class TestRegistryCoversThePublicApi:
    def test_every_exported_metric_is_registered(self) -> None:
        """A metric shipped without a catalogue entry fails here, not in review."""
        missing = _exported_callables() - set(REGISTRY)
        assert not missing, (
            f"Public metrics missing a registry entry: {sorted(missing)}. "
            f"Add a MetricSpec to convexity/registry.py recording the formula, "
            f"units, annualisation behaviour and edge cases."
        )

    def test_every_registered_metric_exists_and_is_callable(self) -> None:
        """An entry naming a function that does not exist fails here too."""
        for name in REGISTRY:
            assert hasattr(cx, name), f"{name} is registered but not exported."
            assert callable(getattr(cx, name)), (
                f"{name} is registered but not callable."
            )

    def test_registry_key_matches_spec_name(self) -> None:
        for key, spec in REGISTRY.items():
            assert key == spec.name


class TestSpecCompleteness:
    @pytest.mark.parametrize("spec", list(REGISTRY.values()), ids=lambda s: s.name)
    def test_required_fields_are_substantive(self, spec: MetricSpec) -> None:
        """Every field a caller relies on must actually say something."""
        assert spec.summary.strip(), f"{spec.name}: empty summary"
        assert spec.formula.strip(), f"{spec.name}: empty formula"
        assert spec.units.strip(), f"{spec.name}: empty units"
        assert spec.annualisation.strip(), f"{spec.name}: empty annualisation"
        assert spec.edge_cases.strip(), f"{spec.name}: empty edge cases"
        assert spec.added_in.strip(), f"{spec.name}: empty added_in"
        assert spec.min_observations >= 1

    @pytest.mark.parametrize("spec", list(REGISTRY.values()), ids=lambda s: s.name)
    def test_categories_and_status_are_enums(self, spec: MetricSpec) -> None:
        assert isinstance(spec.category, Category)
        assert isinstance(spec.status, Status)

    @pytest.mark.parametrize("spec", list(REGISTRY.values()), ids=lambda s: s.name)
    def test_docstring_exists_and_documents_the_contract(
        self, spec: MetricSpec
    ) -> None:
        doc = inspect.getdoc(getattr(cx, spec.name))
        assert doc, f"{spec.name} has no docstring"
        # NumPy-style sections a caller needs in order to trust the number.
        assert "Parameters" in doc, f"{spec.name}: docstring has no Parameters section"
        assert "Returns" in doc, f"{spec.name}: docstring has no Returns section"

    @pytest.mark.parametrize("spec", list(REGISTRY.values()), ids=lambda s: s.name)
    def test_metric_is_fully_annotated(self, spec: MetricSpec) -> None:
        """A typed public API is a product requirement, not a style preference."""
        func = getattr(cx, spec.name)
        signature = inspect.signature(func)
        assert signature.return_annotation is not inspect.Signature.empty, (
            f"{spec.name} has no return annotation"
        )
        for parameter in signature.parameters.values():
            assert parameter.annotation is not inspect.Signature.empty, (
                f"{spec.name}: parameter {parameter.name!r} is unannotated"
            )


class TestContestedDefinitionsCiteSources:
    """Metrics with competing definitions must say which one they implement."""

    @pytest.mark.parametrize(
        "name", ["sortino_ratio", "downside_deviation", "sharpe_ratio", "calmar_ratio"]
    )
    def test_contested_metrics_carry_a_primary_reference(self, name: str) -> None:
        spec = REGISTRY[name]
        assert spec.references, (
            f"{name} has competing definitions in the literature and must cite a "
            f"primary source. Citing another library is not evidence: it imports "
            f"that library's convention choices and its bugs."
        )

    def test_downside_convention_is_documented_in_the_registry(self) -> None:
        spec = REGISTRY["downside_deviation"]
        assert "FULL" in spec.edge_cases
        assert "DOWNSIDE_ONLY" in spec.edge_cases

    def test_calmar_records_its_geometric_numerator(self) -> None:
        """Calmar differs from Sharpe/Sortino here; silence would mislead."""
        assert "GEOMETRIC" in REGISTRY["calmar_ratio"].annualisation.upper()

    def test_sharpe_records_its_arithmetic_numerator(self) -> None:
        assert "rithmetic" in REGISTRY["sharpe_ratio"].edge_cases


class TestRegistryApi:
    def test_get_returns_the_spec(self) -> None:
        assert registry.get("sortino_ratio").name == "sortino_ratio"

    def test_get_raises_for_unknown(self) -> None:
        with pytest.raises(KeyError):
            registry.get("not_a_metric")

    def test_iter_all(self) -> None:
        assert len(list(registry.iter_metrics())) == len(REGISTRY)

    def test_iter_filtered_by_category(self) -> None:
        ratios = list(registry.iter_metrics(Category.RATIO))
        assert {m.name for m in ratios} == {
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "rolling_sharpe",
            "rolling_sortino",
            "rolling_calmar",
        }

    def test_every_category_has_at_least_one_metric(self) -> None:
        for category in Category:
            assert list(registry.iter_metrics(category)), f"{category} is empty"

    def test_spec_is_immutable(self) -> None:
        spec = registry.get("sortino_ratio")
        with pytest.raises((AttributeError, TypeError)):
            spec.name = "changed"  # type: ignore[misc]
