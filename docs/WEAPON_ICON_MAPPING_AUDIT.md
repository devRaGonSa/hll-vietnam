# Weapon Icon Mapping Audit

## Summary

The frontend weapon icon source of truth is now `frontend/assets/js/current-match-weapon-icons.js`, backed only by local SVG files from `frontend/assets/img/weapons/black/`.

The audit focused on avoiding broken image loads, replacing legacy typo filenames, and reusing the same black SVG resolver in the current match kill feed and historical match detail weapon lists.

## Asset Path

- Runtime path: `./assets/img/weapons/black/`
- Filesystem path: `frontend/assets/img/weapons/black/`
- Fallback behavior: if the shared resolver is not available, views render a text fallback instead of loading an old asset path.
- Unknown fallback: `UNKNOWN -> precision_strike_black.svg`

## Local SVG Files Included

The current local set contains 123 SVG files:

- `60l_supply_black.svg`
- `60l_transport_black.svg`
- `at_mine_gs_mk_v_black.svg`
- `ba10_black.svg`
- `bazooka_black.svg`
- `bedford_oyd_supply_black.svg`
- `bedford_oyd_transport_black.svg`
- `bishop_sp_25pdr_black.svg`
- `bombing_run_black.svg`
- `boys_anti_tank_rifle_black.svg`
- `bren_gun_black.svg`
- `browning_m1919_black.svg`
- `canadian_sten_mk_ii_black.svg`
- `churchill_mk_iii_avre_black.svg`
- `churchill_mk_iii_black.svg`
- `churchill_mk_vii_black.svg`
- `colt_1911_black.svg`
- `cromwell_black.svg`
- `crusader_mk_iii_black.svg`
- `enfield_no2_mk_i_black.svg`
- `feldspaten_black.svg`
- `fg42_black.svg`
- `fg42_x4_black.svg`
- `firefly_black.svg`
- `flammenwerfer41_black.svg`
- `flare_gun_black.svg`
- `fn_inglis_no2_mk_i_black.svg`
- `gewehr_black.svg`
- `gmc_cckw_353_supply_black.svg`
- `gmc_cckw_363_supply_black.svg`
- `gmc_cckw_363_transport_black.svg`
- `half_track_black.svg`
- `is_1_black.svg`
- `jeep_black.svg`
- `jeep_willys_black.svg`
- `kar98k_black.svg`
- `kar98k_x8_black.svg`
- `kubelwagen_black.svg`
- `kv2_black.svg`
- `lanchester_black.svg`
- `lee_enfield_jungle_carbine_black.svg`
- `lee_enfield_n4_black.svg`
- `lee_enfield_pattern_1914_black.svg`
- `lee_enfield_pattern_1914_sniper_black.svg`
- `lewis_gun_black.svg`
- `luger_p08_black.svg`
- `m1903_springfield_black.svg`
- `m1903_springfield_sniper_black.svg`
- `m1918a2_bar_black.svg`
- `m1_57mm_cannon_black.svg`
- `m1_carbine_black.svg`
- `m1_garand_black.svg`
- `m1a1_at_mine_black.svg`
- `m24_stielhandgranate_black.svg`
- `m2_ap_mine_black.svg`
- `m2_flamethrower_black.svg`
- `m3_grease_gun_black.svg`
- `m3_half_track_black.svg`
- `m3_knife_black.svg`
- `m43_stielhandgranate_black.svg`
- `m4a3_105mm_black.svg`
- `m8_greyhound_black.svg`
- `m97_black.svg`
- `mg34_black.svg`
- `mg42_black.svg`
- `mills_bomb_black.svg`
- `mk2_grenade_black.svg`
- `mosin_nagant_1891_black.svg`
- `mosin_nagant_9130_black.svg`
- `mosin_nagant_m38_black.svg`
- `mp40_black.svg`
- `mpl50_spade_black.svg`
- `nagant_m1895_black.svg`
- `no82_grenade_black.svg`
- `opel_blitz_supply_black.svg`
- `opel_blitz_transport_black.svg`
- `pak_40_75mm_black.svg`
- `panzer_iii_ausf_n_black.svg`
- `panzerschreck_black.svg`
- `piat_black.svg`
- `pomz_ap_mine_black.svg`
- `ppsh41_black.svg`
- `ppsh_41w_drum_black.svg`
- `precision_strike_black.svg`
- `ptrs41_black.svg`
- `qf_6_pounder_black.svg`
- `rg42_grenade_black.svg`
- `rifle_no4_mk_i_black.svg`
- `rifle_no4_mk_i_sniper_black.svg`
- `rifle_no5_mk_i_black.svg`
- `s_mine_black.svg`
- `satchel_charge_black.svg`
- `scoped_mosin_nagant_9130_black.svg`
- `scoped_svt40_black.svg`
- `sdkfz_121_luchs_black.svg`
- `sdkfz_161_panzer_iv_black.svg`
- `sdkfz_171_panther_black.svg`
- `sdkfz_181_tiger_1_black.svg`
- `sdkfz_234_puma_black.svg`
- `sdkfz_251_half_track_black.svg`
- `sherman_m4a3_75w_black.svg`
- `sherman_m4a3e2_76_black.svg`
- `sherman_m4a3e2_black.svg`
- `smle_no1_mk_iii_black.svg`
- `sten_gun_black.svg`
- `sten_gun_mk_ii_black.svg`
- `stg44_black.svg`
- `strafing_run_black.svg`
- `stuart_m5a1_black.svg`
- `sturmpanzer_iv_black.svg`
- `svt40_black.svg`
- `t34_76_black.svg`
- `t70_black.svg`
- `tellermine_43_black.svg`
- `tetrarch_black.svg`
- `thompson_black.svg`
- `tm35_at_mine_black.svg`
- `tokarev_tt33_black.svg`
- `walther_p38_black.svg`
- `webley_revolver_black.svg`
- `zis2_57mm_cannon_black.svg`
- `zis5_supply_black.svg`
- `zis5_transport_black.svg`

## Inventory Findings

- Tracked SVGs modified in `black/`: 29 existing SVGs.
- Tracked SVGs deleted in `black/`: `browing_m1919_black.svg`, `dp27_black.svg`, `flammenwefer41_black.svg`, `m1_carabine_black.svg`, `mosing_nagant_1891_black.svg`, `mosing_nagant_9130_black.svg`, `mosing_nagant_m38_black.svg`, `panzerchreck_black.svg`, `sten_mk_v_black.svg`.
- New/untracked SVGs in `black/`: 94 files, including corrected names and expanded vehicle, mine, commander, British, Canadian, Soviet and US assets.
- Duplicate by hash: `lee_enfield_jungle_carbine_black.svg` and `rifle_no5_mk_i_black.svg`.
- Suspicious legacy typo names are intentionally not used by runtime JS: `browing`, `mosing`, `panzerchreck`, `flammenwefer`, `m1_carabine`.

## Mapping Corrections

- `browing_m1919_black.svg` is replaced by `browning_m1919_black.svg`.
- `m1_carabine_black.svg` is replaced by `m1_carbine_black.svg`.
- `panzerchreck_black.svg` is replaced by `panzerschreck_black.svg`.
- `flammenwefer41_black.svg` is replaced by `flammenwerfer41_black.svg`.
- `mosing_nagant_*_black.svg` files are replaced by `mosin_nagant_*_black.svg`.
- `sten_mk_v_black.svg` is replaced by the available `sten_gun_black.svg` shared fallback.
- `dp27_black.svg` no longer exists; `DP-27` currently maps to `lewis_gun_black.svg` as the closest local top-feed LMG silhouette.
- The old `weapons/white/` fallback in `partida-actual.js` was removed from the operational path.
- `historico-partida.html` now loads the shared weapon resolver before `historico-partida.js`.
- `historico-partida.js` now renders local black icons for historical `top_weapons` and `death_by` lists when names resolve.

## RCON Names Covered

The runtime covers the 220 explicit RCON/AdminLog names in `CURRENT_MATCH_RCON_WEAPON_ICON_ENTRIES`, including:

- Infantry examples: `GEWEHR 43`, `KARABINER 98K`, `KARABINER 98K x8`, `FG42`, `FG42 x4`, `M1 GARAND`, `M1 CARBINE`, `BROWNING M1919`, `STG44`, `MP40`, `MG34`, `MG42`, `BAZOOKA`, `PANZERSCHRECK`, `PIAT`, `PTRS-41`, `M1918A2 BAR`, `M3 GREASE GUN`, `M97 TRENCH GUN`, `M1A1 THOMPSON`, `M1928A1 THOMPSON`.
- Soviet examples: `MOSIN NAGANT 1891`, `MOSIN NAGANT 91/30`, `MOSIN NAGANT M38`, `SCOPED MOSIN NAGANT 91/30`, `SCOPED SVT40`, `SVT40`, `PPSH 41`, `PPSH 41 W/DRUM`, `TOKAREV TT33`, `NAGANT M1895`.
- British/Canadian examples: `Bren Gun`, `Boys Anti-tank Rifle`, `Sten Gun`, `Sten Gun Mk.II`, `Sten Gun Mk.V`, `Canadian Sten Mk.II`, `Lanchester`, `SMLE No.1 Mk III`, `Rifle No.4 Mk I`, `Rifle No.4 Mk I Sniper`, `Rifle No.5 Mk I`, `PIAT`, `Mills Bomb`, `No.82 Grenade`.
- Vehicles and mounted weapons: `Sd.Kfz.121 Luchs`, `Sd.Kfz.161 Panzer IV`, `Sd.Kfz.171 Panther`, `Sd.Kfz.181 Tiger 1`, `Sd.Kfz.234 Puma`, `Sd.Kfz 251 Half-track`, `Sherman M4A3(75)W`, `Sherman M4A3E2`, `Sherman M4A3E2(76)`, `Stuart M5A1`, `M3 Stuart Honey`, `M8 Greyhound`, `T34/76`, `T70`, `IS-1`, `KV-2`, `BA-10`, `Churchill Mk.III`, `Churchill Mk.VII`, `Cromwell`, `Firefly`, `Tetrarch`.
- Commander, explosives and mines: `BOMBING RUN`, `STRAFING RUN`, `PRECISION STRIKE`, `SATCHEL`, `SATCHEL CHARGE`, `M1A1 AT MINE`, `M2 AP MINE`, `TELLERMINE 43`, `S-MINE`, `POMZ AP MINE`, `TM-35 AT MINE`, `A.T. Mine G.S. Mk V`.
- Logistics vehicles: `GMC CCKW 353 (Supply)`, `GMC CCKW 363 (Supply)`, `GMC CCKW 363 (Transport)`, `Opel Blitz (Supply)`, `Opel Blitz (Transport)`, `ZIS-5 (Supply)`, `ZIS-5 (Transport)`, `Bedford OYD (Supply)`, `Bedford OYD (Transport)`, `Jeep`, `Jeep Willys`, `Kubelwagen`, `60L (Supply)`, `60L (Transport)`.
- Unknown: `UNKNOWN`.

The full exact list remains in `frontend/assets/js/current-match-weapon-icons.js` and is validated by `scripts/validate-weapon-icon-mapping.js`.

## Pending Names Without Dedicated Icon

These are covered by controlled fallbacks but should get dedicated SVGs later if visual accuracy matters:

- `UNKNOWN`
- `MOLOTOV`
- `No.77`
- `Daimler`
- `GAZ-67`
- `DP-27`
- `FairbairnSykes`
- `122MM HOWITZER [M1938 (M-30)]`
- `150MM HOWITZER [sFH 18]`
- `155MM HOWITZER [M114]`
- Generic towed artillery entries that currently reuse closest field-gun or vehicle silhouettes.

## Alias Decisions

- Important aliases remain explicit for common normalized names such as `g43`, `kar98k`, `kar98k x8`, `mp 40`, `m1 garand`, `m1 carbine`, `m1919`, `fg42 scoped`, `fg42 sniper`, `ppsh drum`, `scoped svt40`, `sniper mosin`, `m1a1 thompson`, `m1928 thompson`.
- Legacy typo filenames are not used as asset references.
- Runtime normalization is case-insensitive and strips accents, punctuation, hyphens, brackets and repeated separators into a stable lookup key.
- Vehicle-mounted weapons map to the specific platform icon when a platform SVG exists.
- Shared fallbacks are documented instead of guessed through broad substring matching.

## Production/API Sampling

Commands executed against production:

```powershell
Invoke-RestMethod "https://comunidadhll.devzamode.es/api/current-match/kills?server=comunidad-hispana-01&limit=100"
Invoke-RestMethod "https://comunidadhll.devzamode.es/api/current-match/kills?server=comunidad-hispana-02&limit=100"
Invoke-RestMethod "https://comunidadhll.devzamode.es/api/current-match/players?server=comunidad-hispana-01"
Invoke-RestMethod "https://comunidadhll.devzamode.es/api/current-match/players?server=comunidad-hispana-02"
Invoke-RestMethod "https://comunidadhll.devzamode.es/api/historical/matches/detail?server=comunidad-hispana-01&match=1781023156:1781028555:purpleheartlanewarfare"
```

The endpoints responded, but at the time of this audit they did not expose weapon names in the sampled payloads. The implemented coverage therefore relies on the repository RCON weapon universe from the previous mapping work plus current frontend usage.

## Validation Commands

```powershell
node --check frontend/assets/js/current-match-weapon-icons.js
node --check frontend/assets/js/partida-actual.js
node --check frontend/assets/js/historico-partida.js
node scripts/validate-weapon-icon-mapping.js
git status --short --untracked-files=all
git diff --name-only
```

## Scope Confirmation

- No backend file was modified for weapon icons.
- No RCON host, port, server config, `27001`, Elo/MMR or Comunidad Hispana #03 setting was changed.
- No clan asset was modified by this task.
- No asset outside `frontend/assets/img/weapons/black/` was modified for weapon icons.
- `frontend/assets/img/weapons/black - copia/` and `frontend/assets/img/weapons/black.zip` were not included.
- `tmp/` was not included.
- `ai/system-metrics.md` was not touched by this task; it remains a pre-existing local modification.
