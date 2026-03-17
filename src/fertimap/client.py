"""Public client API for FertiMap."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Iterable, Mapping

import pandas as pd

from fertimap.constants import (
    CALCUL_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_SLEEP_SECONDS,
    DEFAULT_TIMEOUT,
    DETAIL_URL,
)
from fertimap.exceptions import (
    CultureNotFoundError,
    SiteDataNotFoundError,
    UpstreamResponseError,
    ValidationError,
)
from fertimap.models import CultureRule, SiteContext, TargetRequest
from fertimap.parsers import (
    parse_calcul_response,
    parse_culture_rules,
    parse_geo_and_soil,
)
from fertimap.session import build_session
from fertimap.utils import (
    apply_column_map,
    ensure_dataframe,
    generate_rdt_levels,
    get_response_text,
    missing_to_none,
    normalize_culture_name,
    normalize_culture_names,
    validate_coordinates,
    validate_rdt_levels,
    validate_target_yields,
)


class FertiMapClient:
    """Client for querying Fertimap fertilizer recommendations."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: str | None = None,
        session=None,
    ) -> None:
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries
        self.session = session or build_session(
            max_retries=max_retries,
            user_agent=user_agent,
        )

    def get_site_profile(self, longitude: object, latitude: object) -> SiteContext:
        """Fetch and parse site metadata for a coordinate pair."""
        _, _, context, _ = self._fetch_site_payload(longitude, latitude)
        return context

    def list_crops(self, longitude: object, latitude: object) -> pd.DataFrame:
        """Return all crop rules available at a site as a DataFrame."""
        _, _, _, rules = self._fetch_site_payload(longitude, latitude)
        if not rules:
            raise UpstreamResponseError("No crop rules found in Fertimap detail response")
        return pd.DataFrame([asdict(rule) for rule in rules.values()]).sort_values(
            by="culture_id"
        )

    def get_recommendations(
        self,
        longitude: object,
        latitude: object,
        culture_name_en: object | None = None,
        rdt_level: object | None = None,
        target_yield: object | None = None,
        ph: float | None = None,
        matiere_organique_pct: float | None = None,
        p_assimilable_mgkg_p2o5: float | None = None,
        k_mgkg_k2o: float | None = None,
    ) -> pd.DataFrame:
        """Return recommendations for one site.

        Parameters
        ----------
        culture_name_en:
            One crop name, a list/tuple of crop names, or ``None`` for all crops.
        rdt_level:
            One level, many levels, or a delimited string such as ``"low|high"``.
        target_yield:
            One custom numeric target yield or many values. Each value must be
            within the selected crop's ``rdt_min`` and ``rdt_max`` range.
        """
        lon, lat, site_context, culture_rules = self._fetch_site_payload(longitude, latitude)
        selected_rules = self._select_culture_rules(culture_rules, culture_name_en)
        effective_ph = ph if ph is not None else site_context.ph
        effective_mo = (
            matiere_organique_pct
            if matiere_organique_pct is not None
            else site_context.matiere_organique_pct
        )
        effective_p = (
            p_assimilable_mgkg_p2o5
            if p_assimilable_mgkg_p2o5 is not None
            else site_context.p_assimilable_mgkg_p2o5
        )
        effective_k = k_mgkg_k2o if k_mgkg_k2o is not None else site_context.k_mgkg_k2o

        recommendation_rows: list[dict] = []
        for rule in selected_rules:
            target_requests = self._resolve_target_requests(
                culture_rule=rule,
                rdt_level=rdt_level,
                target_yield=target_yield,
            )
            for target_request in target_requests:
                rec = self._fetch_calculation(
                    longitude=lon,
                    latitude=lat,
                    site_context=site_context,
                    culture_rule=rule,
                    target_request=target_request,
                    ph=effective_ph,
                    matiere_organique_pct=effective_mo,
                    p_assimilable_mgkg_p2o5=effective_p,
                    k_mgkg_k2o=effective_k,
                )
                recommendation_rows.append(rec)
                time.sleep(self.sleep_seconds)

        return pd.DataFrame(recommendation_rows)

    def prepare_input_table(
        self,
        data: pd.DataFrame | Iterable[dict] | str,
        column_map: Mapping[str, str] | None = None,
    ) -> pd.DataFrame:
        """Load and align a batch input table to the library schema."""
        frame = ensure_dataframe(data)
        return apply_column_map(frame, column_map=column_map)

    def get_recommendations_batch(
        self,
        data: pd.DataFrame | Iterable[dict] | str,
        column_map: Mapping[str, str] | None = None,
    ) -> pd.DataFrame:
        """Return recommendations for multiple sites.

        ``column_map`` must follow the form ``{"longitude": "lon"}``, meaning
        the user's ``lon`` column should be used as the library's ``longitude`` field.
        """
        frame = self.prepare_input_table(data, column_map=column_map)
        required_columns = {"longitude", "latitude"}
        missing = required_columns - set(frame.columns)
        if missing:
            raise ValidationError(
                f"Batch input is missing required columns: {sorted(missing)}"
            )

        outputs: list[pd.DataFrame] = []
        for input_row_index, (_, row) in enumerate(frame.iterrows()):
            result = self.get_recommendations(
                longitude=missing_to_none(row["longitude"]),
                latitude=missing_to_none(row["latitude"]),
                culture_name_en=missing_to_none(row.get("culture_name_en")),
                rdt_level=missing_to_none(row.get("rdt_level")),
                target_yield=missing_to_none(row.get("target_yield")),
                ph=missing_to_none(row.get("ph")),
                matiere_organique_pct=missing_to_none(row.get("matiere_organique_pct")),
                p_assimilable_mgkg_p2o5=missing_to_none(row.get("p_assimilable_mgkg_p2o5")),
                k_mgkg_k2o=missing_to_none(row.get("k_mgkg_k2o")),
            )
            result.insert(0, "input_row_index", input_row_index)
            outputs.append(result)

        if not outputs:
            return pd.DataFrame()
        return pd.concat(outputs, ignore_index=True)

    # ------------------------------------------------------------------
    # Backward-compatible method aliases from v0.1.x
    # ------------------------------------------------------------------
    def get_site_context(self, longitude: object, latitude: object) -> SiteContext:
        return self.get_site_profile(longitude, latitude)

    def list_available_cultures(self, longitude: object, latitude: object) -> pd.DataFrame:
        return self.list_crops(longitude, latitude)

    def recommend_site(self, *args, **kwargs) -> pd.DataFrame:
        return self.get_recommendations(*args, **kwargs)

    def recommend_many(self, data, column_map: Mapping[str, str] | None = None) -> pd.DataFrame:
        return self.get_recommendations_batch(data, column_map=column_map)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fetch_site_payload(
        self,
        longitude: object,
        latitude: object,
    ) -> tuple[float, float, SiteContext, dict[int, CultureRule]]:
        """Fetch detail HTML once and parse both site and crop metadata."""
        lon, lat = validate_coordinates(longitude, latitude)
        response = self.session.get(
            DETAIL_URL,
            params={"x": lon, "y": lat},
            timeout=self.timeout,
        )
        response.raise_for_status()
        html = get_response_text(response)

        site_context = parse_geo_and_soil(html)
        culture_rules = parse_culture_rules(html)
        if site_context.id_province is None and site_context.soil_type is None and site_context.ph is None:
            raise SiteDataNotFoundError(
                f"No usable site data found for longitude={lon}, latitude={lat}"
            )
        if not culture_rules:
            raise SiteDataNotFoundError(
                f"No crop rules found for longitude={lon}, latitude={lat}"
            )
        return lon, lat, site_context, culture_rules

    def _select_culture_rules(
        self,
        culture_rules: dict[int, CultureRule],
        culture_name_en: object | None,
    ) -> list[CultureRule]:
        """Return either all crop rules or the ones matching the requested names."""
        requested_names = normalize_culture_names(culture_name_en)
        if requested_names is None:
            return list(culture_rules.values())

        available_by_name: dict[str, list[CultureRule]] = {}
        for rule in culture_rules.values():
            normalized = normalize_culture_name(rule.culture_name_en)
            if normalized is not None:
                available_by_name.setdefault(normalized, []).append(rule)

        selected: list[CultureRule] = []
        missing_names: list[str] = []
        for requested_name in requested_names:
            key = normalize_culture_name(requested_name)
            matches = available_by_name.get(key or "", [])
            if not matches:
                missing_names.append(requested_name)
            else:
                selected.extend(matches)

        if missing_names:
            available = sorted(
                rule.culture_name_en for rule in culture_rules.values() if rule.culture_name_en
            )
            raise CultureNotFoundError(
                f"Culture(s) {missing_names!r} not found. Available cultures: {available}"
            )
        return selected

    def _resolve_target_requests(
        self,
        culture_rule: CultureRule,
        rdt_level: object | None,
        target_yield: object | None,
    ) -> list[TargetRequest]:
        """Resolve requested levels and/or custom targets for one crop."""
        use_default_level = target_yield is None
        requested_levels = validate_rdt_levels(
            rdt_level,
            default_when_empty=use_default_level,
        )
        requested_custom_targets = validate_target_yields(target_yield)
        level_to_value = dict(
            generate_rdt_levels(culture_rule.rdt_min, culture_rule.rdt_max, culture_rule.rdt_step)
        )

        target_requests: list[TargetRequest] = []
        for level in requested_levels:
            if level not in level_to_value:
                raise UpstreamResponseError(
                    f"RDT level {level!r} is not available for culture {culture_rule.culture_name_en!r}"
                )
            target_requests.append(
                TargetRequest(
                    request_label=level,
                    request_mode="level",
                    target_yield=level_to_value[level],
                )
            )

        for custom_value in requested_custom_targets:
            self._validate_custom_target_within_rule(custom_value, culture_rule)
            target_requests.append(
                TargetRequest(
                    request_label="custom",
                    request_mode="custom",
                    target_yield=custom_value,
                )
            )

        deduped: list[TargetRequest] = []
        seen: set[tuple[str, float]] = set()
        for request in target_requests:
            key = (request.request_mode, round(request.target_yield, 8))
            if key not in seen:
                seen.add(key)
                deduped.append(request)
        return deduped

    def _validate_custom_target_within_rule(
        self,
        target_yield: float,
        culture_rule: CultureRule,
    ) -> None:
        """Ensure a custom target yield is within Fertimap's allowed range."""
        if culture_rule.rdt_min is None or culture_rule.rdt_max is None:
            raise UpstreamResponseError(
                f"The crop {culture_rule.culture_name_en!r} does not expose target-yield bounds."
            )
        if target_yield < culture_rule.rdt_min or target_yield > culture_rule.rdt_max:
            raise ValidationError(
                f"target_yield={target_yield} is outside the allowed range for "
                f"{culture_rule.culture_name_en!r}: [{culture_rule.rdt_min}, {culture_rule.rdt_max}]"
            )

    def _fetch_calculation(
        self,
        longitude: float,
        latitude: float,
        site_context: SiteContext,
        culture_rule: CultureRule,
        target_request: TargetRequest,
        ph: float | None,
        matiere_organique_pct: float | None,
        p_assimilable_mgkg_p2o5: float | None,
        k_mgkg_k2o: float | None,
    ) -> dict:
        """Call Fertimap calculator endpoint and compose one output row."""
        params = {
            "id_province": site_context.id_province,
            "culture": culture_rule.culture_id,
            "mo": matiere_organique_pct,
            "p": p_assimilable_mgkg_p2o5,
            "k": k_mgkg_k2o,
            "rdt": target_request.target_yield,
            "x_coord": longitude,
            "y_coord": latitude,
        }
        response = self.session.get(CALCUL_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        rec = parse_calcul_response(get_response_text(response))

        return {
            "longitude": longitude,
            "latitude": latitude,
            "region": site_context.region,
            "province": site_context.province,
            "id_province": site_context.id_province,
            "commune": site_context.commune,
            "soil_type": site_context.soil_type,
            "texture_globale": site_context.texture_globale,
            "ph": ph,
            "matiere_organique_pct": matiere_organique_pct,
            "p_assimilable_mgkg_p2o5": p_assimilable_mgkg_p2o5,
            "k_mgkg_k2o": k_mgkg_k2o,
            "slider_rdt_min": site_context.slider_rdt_min,
            "slider_rdt_max": site_context.slider_rdt_max,
            "slider_rdt_step": site_context.slider_rdt_step,
            "slider_rdt_unit": site_context.slider_rdt_unit,
            "culture_id": culture_rule.culture_id,
            "culture_name_raw": culture_rule.culture_name_raw,
            "culture_name_en": culture_rule.culture_name_en,
            "rdt_level": target_request.request_label,
            "target_yield_mode": target_request.request_mode,
            "target_yield": target_request.target_yield,
            "rdt_min_culture": culture_rule.rdt_min,
            "rdt_max_culture": culture_rule.rdt_max,
            "rdt_step_culture": culture_rule.rdt_step,
            "rdt_unit_culture": culture_rule.rdt_unit,
            "rdt_used": target_request.target_yield,
            "N_kg_ha": rec["N_kg_ha"],
            "P_kg_ha": rec["P_kg_ha"],
            "K_kg_ha": rec["K_kg_ha"],
        }
