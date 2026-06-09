# Weapon Icon Black Mapping Analysis

## Resumen ejecutivo

Se cruzó el universo RCON pegado por el usuario con los **220 nombres únicos** consolidados desde `US_WEAPONS`, `SOVIET_WEAPONS`, `BRITISH_WEAPONS`, `CA_WEAPONS`, `AXIS_WEAPONS`, `ALL_WEAPONS` y `NO_SIDE_WEAPONS` (incluyendo `UNKNOWN`) frente a los **123 SVG** presentes en `frontend/assets/img/weapons/black/`.

El resultado deja asignadas todas las armas RCON y hace aparecer todos los iconos `black` en la tabla inversa. Cuando no existe silueta exacta, la asignación se documenta como compartida o fallback, con `confidence=low` en los casos dudosos.

## Conteo

- Armas únicas RCON: **220**
- Iconos `black` encontrados: **123**
- Asignaciones directas (`exact`): **73**
- Asignaciones compartidas (`shared`): **92**
- Asignaciones fallback: **55**
- Asignaciones dudosas (`confidence=low`): **38**
- Iconos usados en la tabla inversa: **123**
- Iconos compartidos por más de un arma: **46**

## Fuentes leídas

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/analyst.md`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/img/weapons/black/`
- `ai/tasks/done/TASK-159-current-match-feed-rollback-and-weapon-icons.md`
- `ai/tasks/done/TASK-135-fix-rcon-match-detail-faction-assets.md`

## Listado completo de SVG en `frontend/assets/img/weapons/black/`

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

## Observaciones sobre el mapping actual de `partida-actual.js`

- El mapping operativo de `frontend/assets/js/partida-actual.js` cubre solo un subconjunto de armas de infantería y algunas aliases de coaxiales/vehículos, no el universo completo RCON.
- Ese mapping trabaja contra la carpeta `white/`, pero sirve para inferir normalizaciones útiles (`GEWEHR 43`, `KARABINER 98K`, `Panzerschreck`, `M1 Garand`, `Mosin`, `Scoped SVT40`, etc.).
- Antes de implementar el mapping `black`, conviene resolverlo en JS con aliases explícitos y sin renombrar SVGs, porque ya hay arrastre de nombres históricos/legacy.

## Tabla principal

| Arma RCON | Facción/origen | WeaponType | Icono asignado | Tipo | Confianza | Notas |
| --- | --- | --- | --- | --- | --- | --- |
| 105MM HOWITZER [M4A3 (105mm)] | US | SPA | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| 122MM HOWITZER [M1938 (M-30)] | SOVIET | Artillery | zis2_57mm_cannon_black.svg | fallback | low | The folder has no Soviet towed howitzer icon; ZiS-2 is the closest Soviet field-gun silhouette. |
| 150MM HOWITZER [sFH 18] | AXIS | Artillery | pak_40_75mm_black.svg | fallback | low | The folder has no Axis towed howitzer icon; Pak 40 is the closest Axis field-gun silhouette. |
| 152MM M-10T [KV-2] | SOVIET | SPA | kv2_black.svg | shared | high | Mounted KV-2 weapons reuse the platform silhouette. |
| 155MM HOWITZER [M114] | US | Artillery | m1_57mm_cannon_black.svg | fallback | low | The folder has no US towed howitzer icon; M1 57mm is the closest US field-gun silhouette. |
| 19-K 45MM [BA-10] | SOVIET | Armor | ba10_black.svg | shared | high | Vehicle-mounted BA-10 weapons reuse the platform silhouette. |
| 20MM KWK 30 [Sd.Kfz.121 Luchs] | AXIS | Armor | sdkfz_121_luchs_black.svg | shared | high | Mounted Luchs weapons reuse the platform silhouette. |
| 230MM PETARD [Churchill Mk III A.V.R.E.] | BRITISH, CA | SPA | churchill_mk_iii_avre_black.svg | shared | high | Mounted AVRE weapons reuse the platform silhouette. |
| 37MM CANNON [M3 Stuart Honey] | BRITISH | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| 37MM CANNON [Stuart M5A1] | CA, US | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| 45MM M1937 [T70] | SOVIET | Armor | t70_black.svg | shared | high | Mounted T70 weapons reuse the platform silhouette. |
| 50mm KwK 39/1 [Sd.Kfz.234 Puma] | AXIS | Armor | sdkfz_234_puma_black.svg | shared | high | Mounted Puma weapons reuse the platform silhouette. |
| 57MM CANNON [M1 57mm] | US | Armor | m1_57mm_cannon_black.svg | fallback | low | The folder has no US towed howitzer icon; M1 57mm is the closest US field-gun silhouette. |
| 57MM CANNON [ZiS-2] | SOVIET | PAK | zis2_57mm_cannon_black.svg | fallback | low | The folder has no Soviet towed howitzer icon; ZiS-2 is the closest Soviet field-gun silhouette. |
| 60L (Supply) | CA | Armor | 60l_supply_black.svg | exact | high | - |
| 60L (Transport) | CA | Armor | 60l_transport_black.svg | exact | high | - |
| 7.5CM KwK 37 [Panzer III Ausf.N] | AXIS | SPA | panzer_iii_ausf_n_black.svg | shared | high | Mounted Panzer III N weapons reuse the platform silhouette. |
| 7.5CM KwK 37 [Sd.Kfz.161 Panzer IV] | AXIS | SPA | sdkfz_161_panzer_iv_black.svg | shared | high | Mounted Panzer IV weapons reuse the platform silhouette. |
| 75MM CANNON [PAK 40] | AXIS | PAK | pak_40_75mm_black.svg | fallback | low | The folder has no Axis towed howitzer icon; Pak 40 is the closest Axis field-gun silhouette. |
| 75MM CANNON [Sd.Kfz.161 Panzer IV] | AXIS | Armor | sdkfz_161_panzer_iv_black.svg | shared | high | Mounted Panzer IV weapons reuse the platform silhouette. |
| 75MM CANNON [Sd.Kfz.171 Panther] | AXIS | Armor | sdkfz_171_panther_black.svg | shared | high | Mounted Panther weapons reuse the platform silhouette. |
| 75MM CANNON [Sherman M4A3(75)W] | CA, US | Armor | sherman_m4a3_75w_black.svg | shared | high | Mounted Sherman M4A3(75)W weapons reuse the platform silhouette. |
| 75MM M3 GUN [Sherman M4A3E2] | US | Armor | sherman_m4a3e2_black.svg | shared | high | Mounted Jumbo 75mm weapons reuse the platform silhouette. |
| 76MM M1 GUN [Sherman M4A3E2(76)] | US | Armor | sherman_m4a3e2_76_black.svg | shared | high | Mounted Jumbo 76mm weapons reuse the platform silhouette. |
| 76MM ZiS-5 [T34/76] | SOVIET | Armor | t34_76_black.svg | shared | high | Mounted T34/76 weapons reuse the platform silhouette. |
| 88 KWK 36 L/56 [Sd.Kfz.181 Tiger 1] | AXIS | Armor | sdkfz_181_tiger_1_black.svg | shared | high | Mounted Tiger I weapons reuse the platform silhouette. |
| A.P. Shrapnel Mine Mk II | BRITISH, CA | Mine | s_mine_black.svg | fallback | medium | The British AP shrapnel mine falls back to the closest anti-personnel mine silhouette present in the folder. |
| A.T. Mine G.S. Mk V | BRITISH, CA | Mine | at_mine_gs_mk_v_black.svg | exact | high | - |
| BA-10 | SOVIET | Armor | ba10_black.svg | shared | high | Vehicle-mounted BA-10 weapons reuse the platform silhouette. |
| BAZOOKA | SOVIET, US | Bazooka | bazooka_black.svg | exact | high | Silhouette reused by US and Soviet bazooka entries because the RCON label is side-agnostic. |
| Bedford OYD (Supply) | BRITISH | Armor | bedford_oyd_supply_black.svg | exact | high | - |
| Bedford OYD (Transport) | BRITISH | Armor | bedford_oyd_transport_black.svg | exact | high | - |
| Bishop SP 25pdr | BRITISH | Armor | bishop_sp_25pdr_black.svg | fallback | medium | The only 25-pounder-related asset is the Bishop SP platform, so the towed QF 25-pounder falls back to the same ordnance family silhouette. |
| BOMBING RUN | NO_SIDE | Commander | bombing_run_black.svg | exact | high | - |
| Boys Anti-tank Rifle | BRITISH | Infantry | boys_anti_tank_rifle_black.svg | exact | high | - |
| Bren Gun | BRITISH, CA | MachineGun | bren_gun_black.svg | exact | high | - |
| BROWNING M1919 | US | MachineGun | browning_m1919_black.svg | exact | high | - |
| Canadian Sten Mk.II | CA | Infantry | canadian_sten_mk_ii_black.svg | exact | high | - |
| Churchill Mk III A.V.R.E. | BRITISH, CA | Armor | churchill_mk_iii_avre_black.svg | shared | high | Mounted AVRE weapons reuse the platform silhouette. |
| Churchill Mk.III | BRITISH | Armor | churchill_mk_iii_black.svg | shared | high | Mounted Churchill Mk.III weapons reuse the platform silhouette. |
| COAXIAL BESA [Cromwell] | BRITISH | Armor | cromwell_black.svg | fallback | low | The generic BESA 7.92mm entry has no platform suffix, so it falls back to the Cromwell icon as a representative British armored BESA platform. |
| COAXIAL BESA [Crusader Mk.III] | BRITISH | Armor | crusader_mk_iii_black.svg | fallback | medium | There is no standalone Crusader RCON platform entry in the pasted file, so the icon is anchored through its mounted weapon strings. |
| COAXIAL BESA [Daimler] | BRITISH, CA | Armor | m8_greyhound_black.svg | fallback | low | No dedicated Daimler icon exists; the closest armored-car silhouette is M8 Greyhound. Exact M8 entries share the same icon. |
| COAXIAL BESA [Tetrarch] | BRITISH | Armor | tetrarch_black.svg | shared | high | Mounted Tetrarch weapons reuse the platform silhouette. |
| COAXIAL BESA 7.92mm | BRITISH | Armor | cromwell_black.svg | fallback | low | The generic BESA 7.92mm entry has no platform suffix, so it falls back to the Cromwell icon as a representative British armored BESA platform. |
| COAXIAL BESA 7.92mm [Churchill Mk III A.V.R.E.] | BRITISH, CA | Armor | churchill_mk_iii_avre_black.svg | shared | high | Mounted AVRE weapons reuse the platform silhouette. |
| COAXIAL BESA 7.92mm [Churchill Mk.III] | BRITISH | Armor | churchill_mk_iii_black.svg | shared | high | Mounted Churchill Mk.III weapons reuse the platform silhouette. |
| COAXIAL BESA 7.92mm [Churchill Mk.VII] | BRITISH | Armor | churchill_mk_vii_black.svg | fallback | medium | No standalone Churchill Mk.VII RCON platform entry is present, so the icon is anchored through its mounted weapon strings. |
| COAXIAL BESA 7.92mm [M4A3 (105mm)] | BRITISH | Armor | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| COAXIAL DT [BA-10] | SOVIET | Armor | ba10_black.svg | shared | high | Vehicle-mounted BA-10 weapons reuse the platform silhouette. |
| COAXIAL DT [IS-1] | SOVIET | Armor | is_1_black.svg | shared | high | Mounted IS-1 weapons reuse the platform silhouette. |
| COAXIAL DT [T34/76] | SOVIET | Armor | t34_76_black.svg | shared | high | Mounted T34/76 weapons reuse the platform silhouette. |
| COAXIAL DT [T70] | SOVIET | Armor | t70_black.svg | shared | high | Mounted T70 weapons reuse the platform silhouette. |
| COAXIAL M1919 [Firefly] | BRITISH, CA | Armor | firefly_black.svg | shared | high | Mounted Firefly weapons reuse the platform silhouette. |
| COAXIAL M1919 [M3 Stuart Honey] | BRITISH | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| COAXIAL M1919 [M4A3 (105mm)] | US | Armor | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| COAXIAL M1919 [M8 Greyhound] | US | Armor | m8_greyhound_black.svg | fallback | low | No dedicated Daimler icon exists; the closest armored-car silhouette is M8 Greyhound. Exact M8 entries share the same icon. |
| COAXIAL M1919 [Sherman M4A3(75)W] | CA, US | Armor | sherman_m4a3_75w_black.svg | shared | high | Mounted Sherman M4A3(75)W weapons reuse the platform silhouette. |
| COAXIAL M1919 [Sherman M4A3E2(76)] | US | Armor | sherman_m4a3e2_76_black.svg | shared | high | Mounted Jumbo 76mm weapons reuse the platform silhouette. |
| COAXIAL M1919 [Sherman M4A3E2] | US | Armor | sherman_m4a3e2_black.svg | shared | high | Mounted Jumbo 75mm weapons reuse the platform silhouette. |
| COAXIAL M1919 [Stuart M5A1] | CA, US | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| COAXIAL MG34 | AXIS | Armor | mg34_black.svg | shared | high | The unsuffixed coaxial MG34 string reuses the MG34 silhouette because no generic vehicle-MG icon exists. |
| COAXIAL MG34 [Panzer III Ausf.N] | AXIS | Armor | panzer_iii_ausf_n_black.svg | shared | high | Mounted Panzer III N weapons reuse the platform silhouette. |
| COAXIAL MG34 [Sd.Kfz.121 Luchs] | AXIS | Armor | sdkfz_121_luchs_black.svg | shared | high | Mounted Luchs weapons reuse the platform silhouette. |
| COAXIAL MG34 [Sd.Kfz.161 Panzer IV] | AXIS | Armor | sdkfz_161_panzer_iv_black.svg | shared | high | Mounted Panzer IV weapons reuse the platform silhouette. |
| COAXIAL MG34 [Sd.Kfz.171 Panther] | AXIS | Armor | sdkfz_171_panther_black.svg | shared | high | Mounted Panther weapons reuse the platform silhouette. |
| COAXIAL MG34 [Sd.Kfz.181 Tiger 1] | AXIS | Armor | sdkfz_181_tiger_1_black.svg | shared | high | Mounted Tiger I weapons reuse the platform silhouette. |
| COAXIAL MG34 [Sd.Kfz.234 Puma] | AXIS | Armor | sdkfz_234_puma_black.svg | shared | high | Mounted Puma weapons reuse the platform silhouette. |
| COLT M1911 | US | Infantry | colt_1911_black.svg | exact | high | - |
| Cromwell | BRITISH | Armor | cromwell_black.svg | fallback | low | The generic BESA 7.92mm entry has no platform suffix, so it falls back to the Cromwell icon as a representative British armored BESA platform. |
| D-5T 85MM [IS-1] | SOVIET | Armor | is_1_black.svg | shared | high | Mounted IS-1 weapons reuse the platform silhouette. |
| Daimler | BRITISH, CA | Armor | m8_greyhound_black.svg | fallback | low | No dedicated Daimler icon exists; the closest armored-car silhouette is M8 Greyhound. Exact M8 entries share the same icon. |
| DP-27 | SOVIET | MachineGun | lewis_gun_black.svg | fallback | medium | El set `black` actual no incluye `dp27_black.svg`; `lewis_gun_black.svg` es la silueta de LMG con cargador superior más cercana. |
| Enfield No.2 Mk I | CA | Infantry | enfield_no2_mk_i_black.svg | exact | high | - |
| FairbairnSykes | BRITISH, CA | Infantry | m3_knife_black.svg | fallback | low | No Fairbairn-Sykes dagger silhouette exists in `black`; M3 knife is the closest melee fallback. |
| FELDSPATEN | AXIS | Infantry | feldspaten_black.svg | exact | high | - |
| FG42 | AXIS | Infantry | fg42_black.svg | exact | high | - |
| FG42 x4 | AXIS | Sniper | fg42_x4_black.svg | exact | high | - |
| Firefly | BRITISH, CA | Armor | firefly_black.svg | shared | high | Mounted Firefly weapons reuse the platform silhouette. |
| FLAMETHROWER | BRITISH, CA | Infantry | m2_flamethrower_black.svg | fallback | low | British/Canadian flamethrower entries have no faction-specific icon; the US flamethrower silhouette is the closest shared fallback. |
| FLAMMENWERFER 41 | AXIS | Infantry | flammenwerfer41_black.svg | exact | high | - |
| FLARE GUN | AXIS, SOVIET, US | Infantry | flare_gun_black.svg | shared | high | British flare pistol is mapped to the same flare silhouette used by the generic FLARE GUN entry. |
| FN-Inglis No 2 MK I | CA | Infantry | fn_inglis_no2_mk_i_black.svg | exact | high | - |
| GAZ-67 | SOVIET | Armor | jeep_black.svg | fallback | medium | GAZ-67 and the Canadian Jeep use the generic jeep silhouette because there is no dedicated GAZ-67 asset. |
| GEWEHR 43 | AXIS | Infantry | gewehr_black.svg | shared | medium | The filename is generic (`gewehr`) but existing frontend aliases already treat it as Gewehr 43. |
| GMC CCKW 353 (Supply) | US | Armor | gmc_cckw_353_supply_black.svg | exact | high | - |
| GMC CCKW 363 (Supply) | US | Armor | gmc_cckw_363_supply_black.svg | exact | high | - |
| GMC CCKW 363 (Transport) | US | Armor | gmc_cckw_363_transport_black.svg | exact | high | - |
| Half-track | CA | Armor | half_track_black.svg | fallback | medium | The Canadian half-track is only available as a generic half-track silhouette, which also serves as fallback for its mounted Browning. |
| HULL BESA [Cromwell] | BRITISH | Armor | cromwell_black.svg | fallback | low | The generic BESA 7.92mm entry has no platform suffix, so it falls back to the Cromwell icon as a representative British armored BESA platform. |
| HULL BESA 7.92mm [Churchill Mk.III] | BRITISH | Armor | churchill_mk_iii_black.svg | shared | high | Mounted Churchill Mk.III weapons reuse the platform silhouette. |
| HULL BESA 7.92mm [Churchill Mk.VII] | BRITISH | Armor | churchill_mk_vii_black.svg | fallback | medium | No standalone Churchill Mk.VII RCON platform entry is present, so the icon is anchored through its mounted weapon strings. |
| HULL BESA 7.92mm [M4A3 (105mm)] | BRITISH | Armor | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| HULL DT [IS-1] | SOVIET | Armor | is_1_black.svg | shared | high | Mounted IS-1 weapons reuse the platform silhouette. |
| HULL DT [KV-2] | SOVIET | Armor | kv2_black.svg | shared | high | Mounted KV-2 weapons reuse the platform silhouette. |
| HULL DT [T34/76] | SOVIET | Armor | t34_76_black.svg | shared | high | Mounted T34/76 weapons reuse the platform silhouette. |
| HULL M1919 [M4A3 (105mm)] | US | Armor | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| HULL M1919 [Sherman M4A3(75)W] | CA, US | Armor | sherman_m4a3_75w_black.svg | shared | high | Mounted Sherman M4A3(75)W weapons reuse the platform silhouette. |
| HULL M1919 [Sherman M4A3E2(76)] | US | Armor | sherman_m4a3e2_76_black.svg | shared | high | Mounted Jumbo 76mm weapons reuse the platform silhouette. |
| HULL M1919 [Sherman M4A3E2] | US | Armor | sherman_m4a3e2_black.svg | shared | high | Mounted Jumbo 75mm weapons reuse the platform silhouette. |
| HULL M1919 [Stuart M5A1] | CA, US | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| HULL MG34 [Sd.Kfz.161 Panzer IV] | AXIS | Armor | sdkfz_161_panzer_iv_black.svg | shared | high | Mounted Panzer IV weapons reuse the platform silhouette. |
| HULL MG34 [Sd.Kfz.171 Panther] | AXIS | Armor | sdkfz_171_panther_black.svg | shared | high | Mounted Panther weapons reuse the platform silhouette. |
| HULL MG34 [Sd.Kfz.181 Tiger 1] | AXIS | Armor | sdkfz_181_tiger_1_black.svg | shared | high | Mounted Tiger I weapons reuse the platform silhouette. |
| IS-1 | SOVIET | Armor | is_1_black.svg | shared | high | Mounted IS-1 weapons reuse the platform silhouette. |
| Jeep | CA | Armor | jeep_black.svg | fallback | medium | GAZ-67 and the Canadian Jeep use the generic jeep silhouette because there is no dedicated GAZ-67 asset. |
| Jeep Willys | BRITISH, US | Armor | jeep_willys_black.svg | exact | high | - |
| KARABINER 98K | AXIS | Infantry | kar98k_black.svg | exact | high | - |
| KARABINER 98K x8 | AXIS | Sniper | kar98k_x8_black.svg | exact | high | - |
| Kubelwagen | AXIS | Armor | kubelwagen_black.svg | exact | high | - |
| KV-2 | SOVIET | Armor | kv2_black.svg | shared | high | Mounted KV-2 weapons reuse the platform silhouette. |
| Lanchester | BRITISH, CA | Infantry | lanchester_black.svg | exact | high | - |
| Lee-Enfield Pattern 1914 | BRITISH | Infantry | lee_enfield_pattern_1914_black.svg | exact | high | - |
| Lee-Enfield Pattern 1914 Sniper | BRITISH | Sniper | lee_enfield_pattern_1914_sniper_black.svg | exact | high | - |
| LeeEnfield Jungle Carbine | BRITISH | Infantry | lee_enfield_jungle_carbine_black.svg | exact | high | Hash comparison shows this SVG is identical to `rifle_no5_mk_i_black.svg`; kept separate because the RCON name still exists. |
| LeeEnfield No.4 Mk I | BRITISH | Infantry | lee_enfield_n4_black.svg | exact | high | Legacy RCON name kept separate from `Rifle No.4 Mk I`. |
| Lewis Gun | BRITISH | MachineGun | lewis_gun_black.svg | fallback | medium | El set `black` actual no incluye `dp27_black.svg`; `lewis_gun_black.svg` es la silueta de LMG con cargador superior más cercana. |
| LUGER P08 | AXIS | Infantry | luger_p08_black.svg | exact | high | - |
| M1 CARBINE | US | Infantry | m1_carbine_black.svg | exact | high | - |
| M1 GARAND | US | Infantry | m1_garand_black.svg | exact | high | - |
| M1903 SPRINGFIELD | US | Sniper | m1903_springfield_sniper_black.svg | exact | high | - |
| M1918A2 BAR | US | Infantry | m1918a2_bar_black.svg | exact | high | - |
| M1919 SPRINGFIELD | US | Sniper | m1903_springfield_black.svg | fallback | medium | Current frontend aliases already use the non-sniper Springfield silhouette for a scoped Springfield label; kept as a legacy/shared mapping candidate. |
| M1928A1 THOMPSON | BRITISH | Infantry | thompson_black.svg | shared | high | Both Thompson variants reuse the same silhouette. |
| M1A1 AT MINE | US | Mine | m1a1_at_mine_black.svg | exact | high | - |
| M1A1 THOMPSON | US | Infantry | thompson_black.svg | shared | high | Both Thompson variants reuse the same silhouette. |
| M2 AP MINE | US | Mine | m2_ap_mine_black.svg | exact | high | - |
| M2 Browning [Half-track] | CA | Armor | half_track_black.svg | fallback | medium | The Canadian half-track is only available as a generic half-track silhouette, which also serves as fallback for its mounted Browning. |
| M2 Browning [M3 Half-track] | SOVIET, US | Armor | m3_half_track_black.svg | shared | medium | No dedicated M2 Browning silhouette exists; the mounted weapon falls back to the M3 Half-track platform icon. |
| M2 FLAMETHROWER | US | Infantry | m2_flamethrower_black.svg | fallback | low | British/Canadian flamethrower entries have no faction-specific icon; the US flamethrower silhouette is the closest shared fallback. |
| M24 STIELHANDGRANATE | AXIS | Grenade | m24_stielhandgranate_black.svg | exact | high | - |
| M3 GREASE GUN | US | Infantry | m3_grease_gun_black.svg | exact | high | - |
| M3 Half-track | BRITISH, SOVIET, US | Armor | m3_half_track_black.svg | shared | medium | No dedicated M2 Browning silhouette exists; the mounted weapon falls back to the M3 Half-track platform icon. |
| M3 KNIFE | US | Infantry | m3_knife_black.svg | fallback | low | No Fairbairn-Sykes dagger silhouette exists in `black`; M3 knife is the closest melee fallback. |
| M3 Stuart Honey | BRITISH | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| M43 STIELHANDGRANATE | AXIS | Grenade | m43_stielhandgranate_black.svg | exact | high | - |
| M4A3 (105mm) | US | Armor | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| M6 37mm [M8 Greyhound] | US | Armor | m8_greyhound_black.svg | fallback | low | No dedicated Daimler icon exists; the closest armored-car silhouette is M8 Greyhound. Exact M8 entries share the same icon. |
| M8 Greyhound | US | Armor | m8_greyhound_black.svg | fallback | low | No dedicated Daimler icon exists; the closest armored-car silhouette is M8 Greyhound. Exact M8 entries share the same icon. |
| M97 TRENCH GUN | US | Infantry | m97_black.svg | shared | high | The icon filename is shortened to `m97`, but it clearly corresponds to the trench gun. |
| MG 42 [Sd.Kfz 251 Half-track] | AXIS | Armor | sdkfz_251_half_track_black.svg | shared | high | Mounted Sd.Kfz 251 weapon reuses the platform silhouette. |
| MG34 | AXIS | MachineGun | mg34_black.svg | shared | high | The unsuffixed coaxial MG34 string reuses the MG34 silhouette because no generic vehicle-MG icon exists. |
| MG42 | AXIS | MachineGun | mg42_black.svg | exact | high | - |
| Mills Bomb | BRITISH, CA | Grenade | mills_bomb_black.svg | exact | high | - |
| MK2 GRENADE | US | Grenade | mk2_grenade_black.svg | exact | high | - |
| MOLOTOV | SOVIET | Grenade | rg42_grenade_black.svg | fallback | low | No dedicated Molotov bottle icon exists in `black`; RG-42 is the closest Soviet throwable fallback. |
| MOSIN NAGANT 1891 | SOVIET | Infantry | mosin_nagant_1891_black.svg | exact | high | - |
| MOSIN NAGANT 91/30 | SOVIET | Infantry | mosin_nagant_9130_black.svg | exact | high | - |
| MOSIN NAGANT M38 | SOVIET | Infantry | mosin_nagant_m38_black.svg | exact | high | - |
| MP40 | AXIS | Infantry | mp40_black.svg | exact | high | - |
| MPL-50 SPADE | SOVIET | Infantry | mpl50_spade_black.svg | exact | high | - |
| NAGANT M1895 | SOVIET | Infantry | nagant_m1895_black.svg | exact | high | - |
| No.2 Mk 5 Flare Pistol | BRITISH, CA | Infantry | flare_gun_black.svg | shared | high | British flare pistol is mapped to the same flare silhouette used by the generic FLARE GUN entry. |
| No.77 | CA | Grenade | no82_grenade_black.svg | fallback | low | No dedicated No.77 grenade icon exists; No.82 is the nearest Commonwealth grenade fallback. |
| No.82 Grenade | BRITISH, CA | Grenade | no82_grenade_black.svg | fallback | low | No dedicated No.77 grenade icon exists; No.82 is the nearest Commonwealth grenade fallback. |
| Opel Blitz (Supply) | AXIS | Armor | opel_blitz_supply_black.svg | exact | high | - |
| Opel Blitz (Transport) | AXIS | Armor | opel_blitz_transport_black.svg | exact | high | - |
| OQF 57MM [Churchill Mk.III] | BRITISH | Armor | churchill_mk_iii_black.svg | shared | high | Mounted Churchill Mk.III weapons reuse the platform silhouette. |
| OQF 57MM [Crusader Mk.III] | BRITISH | Armor | crusader_mk_iii_black.svg | fallback | medium | There is no standalone Crusader RCON platform entry in the pasted file, so the icon is anchored through its mounted weapon strings. |
| OQF 57MM [Sturmpanzer IV] | AXIS | SPA | sturmpanzer_iv_black.svg | fallback | low | The `OQF 57MM [Sturmpanzer IV]` label looks inconsistent but still maps best to the Sturmpanzer IV platform silhouette. |
| OQF 6 - POUNDER Mk.V [Churchill Mk.III] | BRITISH | Armor | churchill_mk_iii_black.svg | shared | high | Mounted Churchill Mk.III weapons reuse the platform silhouette. |
| OQF 75MM [Churchill Mk.VII] | BRITISH | Armor | churchill_mk_vii_black.svg | fallback | medium | No standalone Churchill Mk.VII RCON platform entry is present, so the icon is anchored through its mounted weapon strings. |
| OQF 75MM [Cromwell] | BRITISH | Armor | cromwell_black.svg | fallback | low | The generic BESA 7.92mm entry has no platform suffix, so it falls back to the Cromwell icon as a representative British armored BESA platform. |
| Ordnance QF 6-pounder | CA | PAK | qf_6_pounder_black.svg | shared | high | Canadian and British labels refer to the same 6-pounder gun silhouette. |
| Panzer III Ausf.N | AXIS | Armor | panzer_iii_ausf_n_black.svg | shared | high | Mounted Panzer III N weapons reuse the platform silhouette. |
| PANZERSCHRECK | AXIS | Bazooka | panzerschreck_black.svg | exact | high | - |
| PETARD 230MM  [M4A3 (105mm)] | US | SPA | m4a3_105mm_black.svg | fallback | low | The British BESA references on the M4A3(105) are likely data anomalies, but the closest reviewable fallback remains the M4A3(105) platform icon. |
| PIAT | BRITISH, CA | Infantry | piat_black.svg | exact | high | - |
| POMZ AP MINE | SOVIET | Mine | pomz_ap_mine_black.svg | exact | high | - |
| PPSH 41 | SOVIET | Infantry | ppsh41_black.svg | exact | high | - |
| PPSH 41 W/DRUM | SOVIET | Infantry | ppsh_41w_drum_black.svg | exact | high | - |
| PRECISION STRIKE | NO_SIDE | Commander | precision_strike_black.svg | fallback | low | No dedicated unknown/fallback silhouette exists in `black`; `UNKNOWN` is parked on the most generic commander-strike icon only to keep the review matrix complete. |
| PTRS-41 | SOVIET | Infantry | ptrs41_black.svg | exact | high | - |
| QF 17-POUNDER [Firefly] | BRITISH, CA | Armor | firefly_black.svg | shared | high | Mounted Firefly weapons reuse the platform silhouette. |
| QF 2-POUNDER [Daimler] | BRITISH, CA | Armor | m8_greyhound_black.svg | fallback | low | No dedicated Daimler icon exists; the closest armored-car silhouette is M8 Greyhound. Exact M8 entries share the same icon. |
| QF 2-POUNDER [Tetrarch] | BRITISH | Armor | tetrarch_black.svg | shared | high | Mounted Tetrarch weapons reuse the platform silhouette. |
| QF 25 POUNDER [Bishop SP 25pdr] | BRITISH | SPA | bishop_sp_25pdr_black.svg | fallback | medium | The only 25-pounder-related asset is the Bishop SP platform, so the towed QF 25-pounder falls back to the same ordnance family silhouette. |
| QF 25-POUNDER [QF 25-Pounder] | BRITISH, CA | Artillery | bishop_sp_25pdr_black.svg | fallback | medium | The only 25-pounder-related asset is the Bishop SP platform, so the towed QF 25-pounder falls back to the same ordnance family silhouette. |
| QF 6-POUNDER [QF 6-Pounder] | BRITISH, CA | PAK | qf_6_pounder_black.svg | shared | high | Canadian and British labels refer to the same 6-pounder gun silhouette. |
| QF 75MM [Cromwell] | BRITISH | Armor | cromwell_black.svg | fallback | low | The generic BESA 7.92mm entry has no platform suffix, so it falls back to the Cromwell icon as a representative British armored BESA platform. |
| RG-42 GRENADE | SOVIET | Grenade | rg42_grenade_black.svg | fallback | low | No dedicated Molotov bottle icon exists in `black`; RG-42 is the closest Soviet throwable fallback. |
| Rifle No.4 Mk I | BRITISH, CA | Infantry | rifle_no4_mk_i_black.svg | exact | high | - |
| Rifle No.4 Mk I Sniper | BRITISH, CA | Sniper | rifle_no4_mk_i_sniper_black.svg | exact | high | - |
| Rifle No.5 Mk I | BRITISH | Infantry | rifle_no5_mk_i_black.svg | exact | high | Hash comparison shows this SVG is identical to `lee_enfield_jungle_carbine_black.svg`. |
| S-MINE | AXIS | Mine | s_mine_black.svg | fallback | medium | The British AP shrapnel mine falls back to the closest anti-personnel mine silhouette present in the folder. |
| Satchel | BRITISH, CA | Satchel | satchel_charge_black.svg | shared | high | Three RCON labels collapse into the same satchel silhouette. |
| SATCHEL | AXIS, US | Satchel | satchel_charge_black.svg | shared | high | Three RCON labels collapse into the same satchel silhouette. |
| SATCHEL CHARGE | SOVIET | Satchel | satchel_charge_black.svg | shared | high | Three RCON labels collapse into the same satchel silhouette. |
| SCOPED MOSIN NAGANT 91/30 | SOVIET | Sniper | scoped_mosin_nagant_9130_black.svg | exact | high | - |
| SCOPED SVT40 | SOVIET | Sniper | scoped_svt40_black.svg | exact | high | - |
| Sd.Kfz 251 Half-track | AXIS | Armor | sdkfz_251_half_track_black.svg | shared | high | Mounted Sd.Kfz 251 weapon reuses the platform silhouette. |
| Sd.Kfz.121 Luchs | AXIS | Armor | sdkfz_121_luchs_black.svg | shared | high | Mounted Luchs weapons reuse the platform silhouette. |
| Sd.Kfz.161 Panzer IV | AXIS | Armor | sdkfz_161_panzer_iv_black.svg | shared | high | Mounted Panzer IV weapons reuse the platform silhouette. |
| Sd.Kfz.171 Panther | AXIS | Armor | sdkfz_171_panther_black.svg | shared | high | Mounted Panther weapons reuse the platform silhouette. |
| Sd.Kfz.181 Tiger 1 | AXIS | Armor | sdkfz_181_tiger_1_black.svg | shared | high | Mounted Tiger I weapons reuse the platform silhouette. |
| Sd.Kfz.234 Puma | AXIS | Armor | sdkfz_234_puma_black.svg | shared | high | Mounted Puma weapons reuse the platform silhouette. |
| Sherman M4A3(75)W | CA, US | Armor | sherman_m4a3_75w_black.svg | shared | high | Mounted Sherman M4A3(75)W weapons reuse the platform silhouette. |
| Sherman M4A3E2 | US | Armor | sherman_m4a3e2_black.svg | shared | high | Mounted Jumbo 75mm weapons reuse the platform silhouette. |
| Sherman M4A3E2(76) | US | Armor | sherman_m4a3e2_76_black.svg | shared | high | Mounted Jumbo 76mm weapons reuse the platform silhouette. |
| SMLE No.1 Mk III | BRITISH, CA | Infantry | smle_no1_mk_iii_black.svg | exact | high | - |
| Sten Gun | BRITISH | Infantry | sten_gun_black.svg | shared | medium | The folder has a generic Sten silhouette and a separate Mk.II file; Mk.V is mapped to the generic Sten. |
| Sten Gun Mk.II | BRITISH | Infantry | sten_gun_mk_ii_black.svg | exact | high | - |
| Sten Gun Mk.V | BRITISH | Infantry | sten_gun_black.svg | shared | medium | The folder has a generic Sten silhouette and a separate Mk.II file; Mk.V is mapped to the generic Sten. |
| STG44 | AXIS | Infantry | stg44_black.svg | exact | high | - |
| STRAFING RUN | NO_SIDE | Commander | strafing_run_black.svg | exact | high | - |
| Stuart M5A1 | CA, US | Armor | stuart_m5a1_black.svg | shared | medium | British M3 Stuart Honey falls back to the visually equivalent Stuart M5A1 silhouette. |
| StuH 43 L/12 [Sturmpanzer IV] | AXIS | SPA | sturmpanzer_iv_black.svg | fallback | low | The `OQF 57MM [Sturmpanzer IV]` label looks inconsistent but still maps best to the Sturmpanzer IV platform silhouette. |
| Sturmpanzer IV | AXIS | Armor | sturmpanzer_iv_black.svg | fallback | low | The `OQF 57MM [Sturmpanzer IV]` label looks inconsistent but still maps best to the Sturmpanzer IV platform silhouette. |
| SVT40 | SOVIET | Infantry | svt40_black.svg | exact | high | - |
| T34/76 | SOVIET | Armor | t34_76_black.svg | shared | high | Mounted T34/76 weapons reuse the platform silhouette. |
| T70 | SOVIET | Armor | t70_black.svg | shared | high | Mounted T70 weapons reuse the platform silhouette. |
| TELLERMINE 43 | AXIS | Mine | tellermine_43_black.svg | exact | high | - |
| Tetrarch | BRITISH | Armor | tetrarch_black.svg | shared | high | Mounted Tetrarch weapons reuse the platform silhouette. |
| TM-35 AT MINE | SOVIET | Mine | tm35_at_mine_black.svg | exact | high | - |
| TOKAREV TT33 | SOVIET | Infantry | tokarev_tt33_black.svg | exact | high | - |
| UNKNOWN | NO_SIDE | Unknown | precision_strike_black.svg | fallback | low | No dedicated unknown/fallback silhouette exists in `black`; `UNKNOWN` is parked on the most generic commander-strike icon only to keep the review matrix complete. |
| WALTHER P38 | AXIS | Infantry | walther_p38_black.svg | exact | high | - |
| Webley MK VI | BRITISH | Infantry | webley_revolver_black.svg | shared | high | The icon filename uses the common weapon family name instead of the exact RCON label. |
| ZIS-5 (Supply) | SOVIET | Armor | zis5_supply_black.svg | exact | high | - |
| ZIS-5 (Transport) | SOVIET | Armor | zis5_transport_black.svg | exact | high | - |

## Tabla inversa

| Icono black | Armas RCON asignadas | Notas |
| --- | --- | --- |
| 60l_supply_black.svg | 60L (Supply) | Asignación única. |
| 60l_transport_black.svg | 60L (Transport) | Asignación única. |
| at_mine_gs_mk_v_black.svg | A.T. Mine G.S. Mk V | Asignación única. |
| ba10_black.svg | 19-K 45MM [BA-10], BA-10, COAXIAL DT [BA-10] | Icono compartido por varias armas o variantes. |
| bazooka_black.svg | BAZOOKA | Asignación única. |
| bedford_oyd_supply_black.svg | Bedford OYD (Supply) | Asignación única. |
| bedford_oyd_transport_black.svg | Bedford OYD (Transport) | Asignación única. |
| bishop_sp_25pdr_black.svg | Bishop SP 25pdr, QF 25 POUNDER [Bishop SP 25pdr], QF 25-POUNDER [QF 25-Pounder] | Icono compartido por varias armas o variantes. |
| bombing_run_black.svg | BOMBING RUN | Asignación única. |
| boys_anti_tank_rifle_black.svg | Boys Anti-tank Rifle | Asignación única. |
| bren_gun_black.svg | Bren Gun | Asignación única. |
| browning_m1919_black.svg | BROWNING M1919 | Asignación única. |
| canadian_sten_mk_ii_black.svg | Canadian Sten Mk.II | Asignación única. |
| churchill_mk_iii_avre_black.svg | 230MM PETARD [Churchill Mk III A.V.R.E.], Churchill Mk III A.V.R.E., COAXIAL BESA 7.92mm [Churchill Mk III A.V.R.E.] | Icono compartido por varias armas o variantes. |
| churchill_mk_iii_black.svg | Churchill Mk.III, COAXIAL BESA 7.92mm [Churchill Mk.III], HULL BESA 7.92mm [Churchill Mk.III], OQF 57MM [Churchill Mk.III], OQF 6 - POUNDER Mk.V [Churchill Mk.III] | Icono compartido por varias armas o variantes. |
| churchill_mk_vii_black.svg | COAXIAL BESA 7.92mm [Churchill Mk.VII], HULL BESA 7.92mm [Churchill Mk.VII], OQF 75MM [Churchill Mk.VII] | Icono compartido por varias armas o variantes. |
| colt_1911_black.svg | COLT M1911 | Asignación única. |
| cromwell_black.svg | COAXIAL BESA [Cromwell], COAXIAL BESA 7.92mm, Cromwell, HULL BESA [Cromwell], OQF 75MM [Cromwell], QF 75MM [Cromwell] | Icono compartido por varias armas o variantes. |
| crusader_mk_iii_black.svg | COAXIAL BESA [Crusader Mk.III], OQF 57MM [Crusader Mk.III] | Icono compartido por varias armas o variantes. |
| enfield_no2_mk_i_black.svg | Enfield No.2 Mk I | Asignación única. |
| feldspaten_black.svg | FELDSPATEN | Asignación única. |
| fg42_black.svg | FG42 | Asignación única. |
| fg42_x4_black.svg | FG42 x4 | Asignación única. |
| firefly_black.svg | COAXIAL M1919 [Firefly], Firefly, QF 17-POUNDER [Firefly] | Icono compartido por varias armas o variantes. |
| flammenwerfer41_black.svg | FLAMMENWERFER 41 | Asignación única. |
| flare_gun_black.svg | FLARE GUN, No.2 Mk 5 Flare Pistol | Icono compartido por varias armas o variantes. |
| fn_inglis_no2_mk_i_black.svg | FN-Inglis No 2 MK I | Asignación única. |
| gewehr_black.svg | GEWEHR 43 | Asignación única. |
| gmc_cckw_353_supply_black.svg | GMC CCKW 353 (Supply) | Asignación única. |
| gmc_cckw_363_supply_black.svg | GMC CCKW 363 (Supply) | Asignación única. |
| gmc_cckw_363_transport_black.svg | GMC CCKW 363 (Transport) | Asignación única. |
| half_track_black.svg | Half-track, M2 Browning [Half-track] | Icono compartido por varias armas o variantes. |
| is_1_black.svg | COAXIAL DT [IS-1], D-5T 85MM [IS-1], HULL DT [IS-1], IS-1 | Icono compartido por varias armas o variantes. |
| jeep_black.svg | GAZ-67, Jeep | Icono compartido por varias armas o variantes. |
| jeep_willys_black.svg | Jeep Willys | Asignación única. |
| kar98k_black.svg | KARABINER 98K | Asignación única. |
| kar98k_x8_black.svg | KARABINER 98K x8 | Asignación única. |
| kubelwagen_black.svg | Kubelwagen | Asignación única. |
| kv2_black.svg | 152MM M-10T [KV-2], HULL DT [KV-2], KV-2 | Icono compartido por varias armas o variantes. |
| lanchester_black.svg | Lanchester | Asignación única. |
| lee_enfield_jungle_carbine_black.svg | LeeEnfield Jungle Carbine | Asignación única. |
| lee_enfield_n4_black.svg | LeeEnfield No.4 Mk I | Asignación única. |
| lee_enfield_pattern_1914_black.svg | Lee-Enfield Pattern 1914 | Asignación única. |
| lee_enfield_pattern_1914_sniper_black.svg | Lee-Enfield Pattern 1914 Sniper | Asignación única. |
| lewis_gun_black.svg | DP-27, Lewis Gun | Icono compartido por varias armas o variantes. |
| luger_p08_black.svg | LUGER P08 | Asignación única. |
| m1903_springfield_black.svg | M1919 SPRINGFIELD | Asignación única. |
| m1903_springfield_sniper_black.svg | M1903 SPRINGFIELD | Asignación única. |
| m1918a2_bar_black.svg | M1918A2 BAR | Asignación única. |
| m1_57mm_cannon_black.svg | 155MM HOWITZER [M114], 57MM CANNON [M1 57mm] | Icono compartido por varias armas o variantes. |
| m1_carbine_black.svg | M1 CARBINE | Asignación única. |
| m1_garand_black.svg | M1 GARAND | Asignación única. |
| m1a1_at_mine_black.svg | M1A1 AT MINE | Asignación única. |
| m24_stielhandgranate_black.svg | M24 STIELHANDGRANATE | Asignación única. |
| m2_ap_mine_black.svg | M2 AP MINE | Asignación única. |
| m2_flamethrower_black.svg | FLAMETHROWER, M2 FLAMETHROWER | Icono compartido por varias armas o variantes. |
| m3_grease_gun_black.svg | M3 GREASE GUN | Asignación única. |
| m3_half_track_black.svg | M2 Browning [M3 Half-track], M3 Half-track | Icono compartido por varias armas o variantes. |
| m3_knife_black.svg | FairbairnSykes, M3 KNIFE | Icono compartido por varias armas o variantes. |
| m43_stielhandgranate_black.svg | M43 STIELHANDGRANATE | Asignación única. |
| m4a3_105mm_black.svg | 105MM HOWITZER [M4A3 (105mm)], COAXIAL BESA 7.92mm [M4A3 (105mm)], COAXIAL M1919 [M4A3 (105mm)], HULL BESA 7.92mm [M4A3 (105mm)], HULL M1919 [M4A3 (105mm)], M4A3 (105mm), PETARD 230MM  [M4A3 (105mm)] | Icono compartido por varias armas o variantes. |
| m8_greyhound_black.svg | COAXIAL BESA [Daimler], COAXIAL M1919 [M8 Greyhound], Daimler, M6 37mm [M8 Greyhound], M8 Greyhound, QF 2-POUNDER [Daimler] | Icono compartido por varias armas o variantes. |
| m97_black.svg | M97 TRENCH GUN | Asignación única. |
| mg34_black.svg | COAXIAL MG34, MG34 | Icono compartido por varias armas o variantes. |
| mg42_black.svg | MG42 | Asignación única. |
| mills_bomb_black.svg | Mills Bomb | Asignación única. |
| mk2_grenade_black.svg | MK2 GRENADE | Asignación única. |
| mosin_nagant_1891_black.svg | MOSIN NAGANT 1891 | Asignación única. |
| mosin_nagant_9130_black.svg | MOSIN NAGANT 91/30 | Asignación única. |
| mosin_nagant_m38_black.svg | MOSIN NAGANT M38 | Asignación única. |
| mp40_black.svg | MP40 | Asignación única. |
| mpl50_spade_black.svg | MPL-50 SPADE | Asignación única. |
| nagant_m1895_black.svg | NAGANT M1895 | Asignación única. |
| no82_grenade_black.svg | No.77, No.82 Grenade | Icono compartido por varias armas o variantes. |
| opel_blitz_supply_black.svg | Opel Blitz (Supply) | Asignación única. |
| opel_blitz_transport_black.svg | Opel Blitz (Transport) | Asignación única. |
| pak_40_75mm_black.svg | 150MM HOWITZER [sFH 18], 75MM CANNON [PAK 40] | Icono compartido por varias armas o variantes. |
| panzer_iii_ausf_n_black.svg | 7.5CM KwK 37 [Panzer III Ausf.N], COAXIAL MG34 [Panzer III Ausf.N], Panzer III Ausf.N | Icono compartido por varias armas o variantes. |
| panzerschreck_black.svg | PANZERSCHRECK | Asignación única. |
| piat_black.svg | PIAT | Asignación única. |
| pomz_ap_mine_black.svg | POMZ AP MINE | Asignación única. |
| ppsh41_black.svg | PPSH 41 | Asignación única. |
| ppsh_41w_drum_black.svg | PPSH 41 W/DRUM | Asignación única. |
| precision_strike_black.svg | PRECISION STRIKE, UNKNOWN | Icono compartido por varias armas o variantes. |
| ptrs41_black.svg | PTRS-41 | Asignación única. |
| qf_6_pounder_black.svg | Ordnance QF 6-pounder, QF 6-POUNDER [QF 6-Pounder] | Icono compartido por varias armas o variantes. |
| rg42_grenade_black.svg | MOLOTOV, RG-42 GRENADE | Icono compartido por varias armas o variantes. |
| rifle_no4_mk_i_black.svg | Rifle No.4 Mk I | Asignación única. |
| rifle_no4_mk_i_sniper_black.svg | Rifle No.4 Mk I Sniper | Asignación única. |
| rifle_no5_mk_i_black.svg | Rifle No.5 Mk I | Asignación única. |
| s_mine_black.svg | A.P. Shrapnel Mine Mk II, S-MINE | Icono compartido por varias armas o variantes. |
| satchel_charge_black.svg | Satchel, SATCHEL, SATCHEL CHARGE | Icono compartido por varias armas o variantes. |
| scoped_mosin_nagant_9130_black.svg | SCOPED MOSIN NAGANT 91/30 | Asignación única. |
| scoped_svt40_black.svg | SCOPED SVT40 | Asignación única. |
| sdkfz_121_luchs_black.svg | 20MM KWK 30 [Sd.Kfz.121 Luchs], COAXIAL MG34 [Sd.Kfz.121 Luchs], Sd.Kfz.121 Luchs | Icono compartido por varias armas o variantes. |
| sdkfz_161_panzer_iv_black.svg | 7.5CM KwK 37 [Sd.Kfz.161 Panzer IV], 75MM CANNON [Sd.Kfz.161 Panzer IV], COAXIAL MG34 [Sd.Kfz.161 Panzer IV], HULL MG34 [Sd.Kfz.161 Panzer IV], Sd.Kfz.161 Panzer IV | Icono compartido por varias armas o variantes. |
| sdkfz_171_panther_black.svg | 75MM CANNON [Sd.Kfz.171 Panther], COAXIAL MG34 [Sd.Kfz.171 Panther], HULL MG34 [Sd.Kfz.171 Panther], Sd.Kfz.171 Panther | Icono compartido por varias armas o variantes. |
| sdkfz_181_tiger_1_black.svg | 88 KWK 36 L/56 [Sd.Kfz.181 Tiger 1], COAXIAL MG34 [Sd.Kfz.181 Tiger 1], HULL MG34 [Sd.Kfz.181 Tiger 1], Sd.Kfz.181 Tiger 1 | Icono compartido por varias armas o variantes. |
| sdkfz_234_puma_black.svg | 50mm KwK 39/1 [Sd.Kfz.234 Puma], COAXIAL MG34 [Sd.Kfz.234 Puma], Sd.Kfz.234 Puma | Icono compartido por varias armas o variantes. |
| sdkfz_251_half_track_black.svg | MG 42 [Sd.Kfz 251 Half-track], Sd.Kfz 251 Half-track | Icono compartido por varias armas o variantes. |
| sherman_m4a3_75w_black.svg | 75MM CANNON [Sherman M4A3(75)W], COAXIAL M1919 [Sherman M4A3(75)W], HULL M1919 [Sherman M4A3(75)W], Sherman M4A3(75)W | Icono compartido por varias armas o variantes. |
| sherman_m4a3e2_76_black.svg | 76MM M1 GUN [Sherman M4A3E2(76)], COAXIAL M1919 [Sherman M4A3E2(76)], HULL M1919 [Sherman M4A3E2(76)], Sherman M4A3E2(76) | Icono compartido por varias armas o variantes. |
| sherman_m4a3e2_black.svg | 75MM M3 GUN [Sherman M4A3E2], COAXIAL M1919 [Sherman M4A3E2], HULL M1919 [Sherman M4A3E2], Sherman M4A3E2 | Icono compartido por varias armas o variantes. |
| smle_no1_mk_iii_black.svg | SMLE No.1 Mk III | Asignación única. |
| sten_gun_black.svg | Sten Gun, Sten Gun Mk.V | Icono compartido por varias armas o variantes. |
| sten_gun_mk_ii_black.svg | Sten Gun Mk.II | Asignación única. |
| stg44_black.svg | STG44 | Asignación única. |
| strafing_run_black.svg | STRAFING RUN | Asignación única. |
| stuart_m5a1_black.svg | 37MM CANNON [M3 Stuart Honey], 37MM CANNON [Stuart M5A1], COAXIAL M1919 [M3 Stuart Honey], COAXIAL M1919 [Stuart M5A1], HULL M1919 [Stuart M5A1], M3 Stuart Honey, Stuart M5A1 | Icono compartido por varias armas o variantes. |
| sturmpanzer_iv_black.svg | OQF 57MM [Sturmpanzer IV], StuH 43 L/12 [Sturmpanzer IV], Sturmpanzer IV | Icono compartido por varias armas o variantes. |
| svt40_black.svg | SVT40 | Asignación única. |
| t34_76_black.svg | 76MM ZiS-5 [T34/76], COAXIAL DT [T34/76], HULL DT [T34/76], T34/76 | Icono compartido por varias armas o variantes. |
| t70_black.svg | 45MM M1937 [T70], COAXIAL DT [T70], T70 | Icono compartido por varias armas o variantes. |
| tellermine_43_black.svg | TELLERMINE 43 | Asignación única. |
| tetrarch_black.svg | COAXIAL BESA [Tetrarch], QF 2-POUNDER [Tetrarch], Tetrarch | Icono compartido por varias armas o variantes. |
| thompson_black.svg | M1928A1 THOMPSON, M1A1 THOMPSON | Icono compartido por varias armas o variantes. |
| tm35_at_mine_black.svg | TM-35 AT MINE | Asignación única. |
| tokarev_tt33_black.svg | TOKAREV TT33 | Asignación única. |
| walther_p38_black.svg | WALTHER P38 | Asignación única. |
| webley_revolver_black.svg | Webley MK VI | Asignación única. |
| zis2_57mm_cannon_black.svg | 122MM HOWITZER [M1938 (M-30)], 57MM CANNON [ZiS-2] | Icono compartido por varias armas o variantes. |
| zis5_supply_black.svg | ZIS-5 (Supply) | Asignación única. |
| zis5_transport_black.svg | ZIS-5 (Transport) | Asignación única. |

## Iconos con nombre sospechoso o silueta dudosa

- `partida-actual.js` sigue referenciando nombres legacy/erróneos en blanco como `browing_m1919`, `flammenwefer41`, `m1_carabine`, `mosing_nagant_*`, `panzerchreck` y `sten_mk_v`.
- `gewehr_black.svg` es demasiado genérico para un mapeo exacto a `GEWEHR 43`.
- `m1903_springfield_black.svg` y `m1903_springfield_sniper_black.svg` sugieren dos usos para una familia que en RCON llega como sniper.
- `lee_enfield_jungle_carbine_black.svg` y `rifle_no5_mk_i_black.svg` son SVG idénticos por hash.
- `precision_strike_black.svg` se reutiliza como placeholder de `UNKNOWN` solo para cerrar la matriz documental; no es una decisión de implementación final.

## Recomendación de siguiente paso

- El mapping puede implementarse directamente en JS mediante una tabla de aliases y resolución a `black/`, sin renombrar archivos.
- No conviene renombrar SVGs ahora: hay nombres legacy ya consumidos por el frontend (`browing`, `mosing`, `panzerchreck`, etc.) y es más seguro encapsular la normalización en código.
- Faltan siluetas específicas para varios casos (`Daimler`, `GAZ-67`, `Molotov`, `No.77`, howitzers remolcados y un icono genérico `UNKNOWN`), pero el documento ya propone fallbacks revisables.
- Antes de aplicar el mapping operativo, conviene revisar manualmente los casos `confidence=low`, especialmente `UNKNOWN`, `MOLOTOV`, `FLAMETHROWER`, `Daimler`, `QF 25-POUNDER [QF 25-Pounder]`, `150MM HOWITZER [sFH 18]` y las referencias BESA sobre `M4A3 (105mm)`.

## Validación documental

- Todas las armas únicas del universo RCON consolidado (220) tienen icono asignado.
- Todos los SVG de `frontend/assets/img/weapons/black/` (123) aparecen en la tabla inversa.
- No se modificó ningún SVG.
- No se tocó backend.
- No se hizo push.

## Implementación aplicada

- Runtime aplicado en `frontend/assets/js/current-match-weapon-icons.js`.
- Consumo del runtime activado desde `frontend/partida-actual.html` y `frontend/assets/js/partida-actual.js`.
- Estrategia usada:
  - 220 entradas RCON exactas `arma -> svg black`
  - aliases explícitos para nombres legacy o coloquiales ya soportados por el frontend
  - fallback `UNKNOWN -> precision_strike_black.svg`
  - fallback documentado para `MOLOTOV`, `No.77`, `Daimler`, `GAZ-67`, howitzers remolcados y `FairbairnSykes`
- Cobertura implementada: 220 armas únicas RCON más aliases legacy.
- Casos que siguen requiriendo icono nuevo futuro:
  - `UNKNOWN`
  - `MOLOTOV`
  - `No.77`
  - `Daimler`
  - `GAZ-67`
  - `122MM HOWITZER [M1938 (M-30)]`
  - `155MM HOWITZER [M114]`
  - `150MM HOWITZER [sFH 18]`
  - opcionalmente `FairbairnSykes`
  - opcionalmente `DP-27`
