<table border="0">
 <tr>
    <td><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/University_of_Prishtina_logo.svg/1200px-University_of_Prishtina_logo.svg.png" width="150" alt="University Logo" /></td>
    <td>
      <p>Universiteti i Prishtinës</p>
      <p>Fakulteti i Inxhinierisë Elektrike dhe Kompjuterike</p>
      <p>Inxhinieri Kompjuterike dhe Softuerike - Programi Master</p>
      <p>Profesor: Prof. Dr. Kadri Sylejmani</p>
      <p>Asistent: MSc. Labeat Arbneshi</p>
    </td>
 </tr>
</table>

# Optimizimi i Orarit Televiziv

Ky projekt trajton problemin e planifikimit televiziv për hapësira publike. Qëllimi është të ndërtohet një orar valid duke zgjedhur programe nga shumë kanale, në mënyrë që të maksimizohet rezultati total i shikueshmërisë.

Problemi është kombinatorial, sepse në çdo moment mund të ketë shumë programe të mundshme, ndërsa një zgjedhje e hershme mund të ndikojë shumë në mundësitë e mëvonshme. Për këtë arsye projekti përdor heuristika të avancuara, kryesisht `Beam Search`, `Beam Search` me randomness të kontrolluar dhe `Rank-based Ant Colony Optimization`.

## Kufizimet Kryesore

Zgjidhjet e gjeneruara duhet të respektojnë kufizimet e problemit:

- `Time window`: programet duhet të planifikohen brenda intervalit global të hapjes dhe mbylljes.
- `No overlap`: në ekran mund të shfaqet vetëm një program në një moment kohe.
- `Minimum duration`: segmentet e planifikuara duhet të zgjasin së paku `D` minuta. Nëse programi origjinal është më i shkurtër se `D`, ai mund të përdoret vetëm si program i plotë.
- `Genre repetition`: kufizohet numri i programeve të njëpasnjëshme me të njëjtin zhanër.
- `Priority blocks`: në disa intervale kohore lejohen vetëm kanale të caktuara.
- `Time preferences`: disa zhanre marrin bonus në intervale të caktuara kohore.
- `Penalties`: ndërrimi i kanalit dhe ndërprerja ose nisja jo natyrale e programit mund të sjellë penalizime.

## Algoritmet

### Beam Search

`BeamSearchScheduler` ndodhet në:

```text
scheduler/beam_search_scheduler.py
```

Beam Search ndërton orarin hap pas hapi dhe në çdo hap mban vetëm disa zgjidhje të pjesshme më të mira. Kjo e bën më të fortë se një qasje thjesht greedy, sepse nuk ndjek vetëm një rrugë të vetme.

Parametrat kryesorë:

- `beam_width = 100`
- `lookahead = 4`
- `density_percentile = 25`

Ky scheduler përfshin edhe logjikën kryesore për:

- gjenerimin e kandidatëve validë
- llogaritjen e score-it
- kontrollin e kufizimeve
- local search final

Këto pjesë ripërdoren edhe nga ACO scheduler.

### Beam Search me Randomness

Në versionin e përmirësuar, Beam Search u zgjerua me randomness të kontrolluar. Ideja nuk është të zgjidhen programe rastësisht, por të diversifikohet zgjedhja mes kandidatëve afër më të mirëve.

Pra algoritmi:

- mban kandidatët më të fortë në mënyrë deterministike
- për disa vende në beam, zgjedh nga një grup kandidatësish të mirë, por të përzier
- përdor `seed` për riprodhueshmëri kur kërkohet
- përdor `restarts` për të provuar disa kalime të randomizuara

Kjo e ndihmon algoritmin të mos ngecë gjithmonë në të njëjtën rrugë lokale.

Komandë shembull:

```bash
python main.py --algorithm beam -i data/input/kosovo_tv_input.json --restarts 3 --seed 123 --verbose
```

Nëse dëshirohet versioni deterministik:

```bash
python main.py --algorithm beam -i data/input/kosovo_tv_input.json --disable-randomness
```

### Rank-based Ant Colony Optimization

`RankBasedAcoScheduler` ndodhet në:

```text
scheduler/rank_based_aco_scheduler.py
```

Ky scheduler implementon një variant `Rank-based ACO`. Çdo ant ndërton një orar të plotë valid. Pas çdo iterimi, zgjidhjet renditen sipas score-it dhe vetëm ants më të mirë e përforcojnë feromonin.

Në versionin final u shtua edhe `elite carryover`. Kjo do të thotë që zgjidhja më e mirë globale futet përsëri në listën e kandidatëve të iterimit pasues. Prandaj score-i më i mirë i raportuar brenda iterimeve nuk bie nën `global_best`, sepse kolonia nuk e harron rrugën më të mirë të gjetur deri në atë moment.

ACO përdor këtë formulë për të llogaritur peshën e një kandidati:

```text
weight = pheromone^alpha * heuristic^beta * memory_factor
```

Kuptimi:

- `pheromone`: çfarë ka mësuar algoritmi nga zgjidhjet e mira.
- `heuristic`: sa i mirë duket kandidati në momentin aktual.
- `memory_factor`: sinjal shtesë nga memory e tranzicioneve të mira në kohë të caktuara.

Parametrat kryesorë të ekspozuar në CLI janë:

- `--ants`: numri i ants për iterim
- `--iterations`: numri i iterimeve ACO
- `--alpha`: rëndësia e feromonit
- `--beta`: rëndësia e heuristikës
- `--rho`: shkalla e avullimit të feromonit
- `--candidate-cap`: numri maksimal i kandidatëve që shqyrtohen në një hap
- `--exploitation-prob`: probabiliteti që ant-i të zgjedhë direkt kandidatin më të fortë
- `--memory-strength`: ndikimi i memory në peshën e kandidatit
- `--seed`: vlerë për riprodhueshmëri
- `--run-id`: etiketë për të ruajtur çdo run veçmas
- `--local-search-iters`: numri i tentimeve të ACO local search pas iterimeve kryesore; vlera `0` e çaktivizon

Parametrat më të avancuar ekzistojnë në kod, por për eksperimentimin fillestar janë mbajtur me vlera fikse:

- `top_k = 3`
- `tau0 = 1.0`
- `tau_min = 0.1`
- `tau_max = 5.0`
- `time_bucket_size = 60`

## Time-Transition Memory

Për të përmbushur kërkesën që ants të ruajnë informacion gjatë ekzekutimit, ACO u zgjerua me `time-transition memory`.

Memory ruan informacione në formën:

```text
(time_bucket, previous_channel, next_channel, next_genre)
```

Shembull:

```text
(2, 4, 7, "sports")
```

Kjo do të thotë që në bucket-in kohor `2`, kalimi nga kanali `4` në kanalin `7`, drejt një programi `sports`, ka dalë i dobishëm në zgjidhje të mira.

Në iterimet e ardhshme, nëse një ant ndodhet në një situatë të ngjashme, ky kandidat merr një peshë më të madhe. Memory nuk e detyron zgjedhjen, por e bën atë më të mundshme.

Memory gjithashtu avullon me kohë, njësoj si feromoni. Kjo e lejon algoritmin të mbajë mend sinjale të mira, por të mos bllokohet përgjithmonë në vendime të hershme.

## ACO Local Search

Pas përfundimit të iterimeve kryesore të ACO-së, zgjidhja më e mirë kalon në një fazë përmirësimi lokale. Kjo fazë nuk e rindërton orarin me greedy, por përdor përsëri ACO.

Logjika është:

- merret `global_best` nga ACO
- gjendet zona më e dobët e orarit sipas score-it për minutë
- ruhet prefix-i para asaj zone
- pjesa pas saj rindërtohet me ants, pheromone, heuristic dhe memory
- nëse zgjidhja e re ka score më të lartë, ajo pranohet

Zona më e dobët gjendet me `weakest-window`. Scheduler shikon dritare të vogla programesh radhazi, rreth `20%` të orarit, por jo më shumë se `8` programe. Dritarja me dendësinë më të ulët të score-it përdoret si sinjal se ku ka më shumë potencial për përmirësim.

Ky local search është i mbrojtshëm sepse nuk është random dhe nuk përdor një algoritëm tjetër. Ai përdor të njëjtat parametra të ACO-së, por nis nga një prefix i ruajtur i zgjidhjes aktuale.

Output-et e këtij varianti ruhen me emrin:

```text
<instance>_output_aco_localsearch_rank_<run_id>_<score>.json
```

## Hyperparameter Tuning

Për ACO u shtua mundësia e ekzekutimit të shumë konfigurimeve me parametra të ndryshëm. Kjo bëhet për të analizuar se cilat vlera japin score më të mirë për instanca të ndryshme.

Për këtë arsye:

- parametrat e dhënë nga user-i respektohen nga scheduler
- nuk bëhet më ulje automatike e ants ose iterations për instanca të mëdha
- çdo run mund të ruhet me `--run-id`
- output-et e ACO ruhen të ndara nga output-et e beam/randomness

Komandë shembull për tuning:

```bash
python main.py --algorithm aco -i data/input/germany_tv_input.json -o data/output_aco_tuning/germany --run-id r01 --ants 12 --iterations 10 --alpha 1.0 --beta 2.0 --rho 0.15 --candidate-cap 10 --exploitation-prob 0.80 --memory-strength 0.50 --seed 701 --verbose
```

Output-i ruhet me formatin:

```text
<instance>_output_<algorithm>_<run_id>_<score>.json
```

Shembull:

```text
germany_tv_output_aco_rank_r01_1553.json
```

## Rezultatet e plota ACO

Rezultatet e mëposhtme janë marrë nga raporti `Raportet ACO.xlsx`. Për secilën instancë janë paraqitur të gjitha ekzekutimet e regjistruara, ndërsa rreshti më i mirë është shënuar me **bold**.

<details>
<summary><strong>australia_iptv</strong> - 12 runs, best score 4833 (r10)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 201 | 10 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 4684 | australia_iptv_output_aco_rank_r01_4684.json |
| r02 | 202 | 10 | 12 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 4598 | australia_iptv_output_aco_rank_r02_4598.json |
| r03 | 203 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 4819 | australia_iptv_output_aco_rank_r03_4819.json |
| r04 | 204 | 10 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 4725 | australia_iptv_output_aco_rank_r04_4725.json |
| r05 | 205 | 10 | 10 | 1 | 2.5 | 0.15 | 10 | 0.8 | 0.5 | 4680 | australia_iptv_output_aco_rank_r05_4680.json |
| r06 | 206 | 10 | 10 | 1 | 2 | 0.1 | 10 | 0.8 | 0.5 | 4685 | australia_iptv_output_aco_rank_r06_4685.json |
| r07 | 207 | 10 | 10 | 1 | 2 | 0.15 | 12 | 0.8 | 0.5 | 4641 | australia_iptv_output_aco_rank_r07_4641.json |
| r08 | 208 | 10 | 10 | 1 | 2 | 0.15 | 10 | 0.85 | 0.7 | 4592 | australia_iptv_output_aco_rank_r08_4592.json |
| r09 | 209 | 12 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 4685 | australia_iptv_output_aco_rank_r09_4685.json |
| **r10** | **210** | **14** | **10** | **1.3** | **2** | **0.15** | **10** | **0.8** | **0.5** | **4833** | **australia_iptv_output_aco_rank_r10_4833.json** |
| r11 | 211 | 12 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 4586 | australia_iptv_output_aco_rank_r11_4586.json |
| r12 | 212 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 4498 | australia_iptv_output_aco_rank_r12_4498.json |

</details>

<details>
<summary><strong>canada_pw</strong> - 10 runs, best score 5972 (r02)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 301 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5826 | canada_pw_output_aco_rank_r01_5826.json |
| **r02** | **302** | **14** | **10** | **1** | **2** | **0.15** | **10** | **0.8** | **0.5** | **5972** | **canada_pw_output_aco_rank_r02_5972.json** |
| r03 | 303 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r03_5972.json |
| r04 | 304 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r04_5972.json |
| r05 | 305 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r05_5972.json |
| r06 | 306 | 16 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r06_5972.json |
| r07 | 307 | 12 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r07_5972.json |
| r08 | 308 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r08_5972.json |
| r09 | 309 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r09_5972.json |
| r10 | 310 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 5972 | canada_pw_output_aco_rank_r10_5972.json |

</details>

<details>
<summary><strong>china_pw</strong> - 10 runs, best score 2830 (r07)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 401 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2778 | china_pw_output_aco_rank_r01_2778.json |
| r02 | 402 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2816 | china_pw_output_aco_rank_r01_2816.json |
| r03 | 403 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2817 | china_pw_output_aco_rank_r03_2817.json |
| r04 | 404 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2814 | china_pw_output_aco_rank_r04_2814.json |
| r05 | 405 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2813 | china_pw_output_aco_rank_r05_2813.json |
| r06 | 406 | 16 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2817 | china_pw_output_aco_rank_r06_2817.json |
| **r07** | **407** | **12** | **10** | **1.3** | **2** | **0.15** | **10** | **0.8** | **0.5** | **2830** | **china_pw_output_aco_rank_r07_2830.json** |
| r08 | 408 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2822 | china_pw_output_aco_rank_r08_2822.json |
| r09 | 409 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2814 | china_pw_output_aco_rank_r09_2814.json |
| r10 | 410 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 2817 | china_pw_output_aco_rank_r10_2817.json |

</details>

<details>
<summary><strong>croatia_tv</strong> - 10 runs, best score 2203 (r01)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **r01** | **501** | **12** | **10** | **1** | **2** | **0.15** | **10** | **0.8** | **0.5** | **2203** | **croatia_tv_output_aco_rank_r01_2203.json** |
| r02 | 502 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r02_2203.json |
| r03 | 503 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r03_2203.json |
| r04 | 504 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r04_2203.json |
| r05 | 505 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r05_2203.json |
| r06 | 506 | 16 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r06_2203.json |
| r07 | 507 | 12 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r07_2203.json |
| r08 | 508 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r08_2203.json |
| r09 | 509 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r09_2203.json |
| r10 | 510 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 2203 | croatia_tv_output_aco_rank_r10_2203.json |

</details>

<details>
<summary><strong>france_iptv</strong> - 10 runs, best score 11417 (r05)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 601 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 11267 | france_iptv_output_aco_rank_r01_11267.json |
| r02 | 602 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 10924 | france_iptv_output_aco_rank_r02_10924.json |
| r03 | 603 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 10766 | france_iptv_output_aco_rank_r03_10766.json |
| r04 | 604 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 11192 | france_iptv_output_aco_rank_r04_11192.json |
| **r05** | **605** | **14** | **10** | **1.2** | **2** | **0.15** | **10** | **0.8** | **0.5** | **11417** | **france_iptv_output_aco_rank_r05_11417.json** |
| r06 | 606 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 10648 | france_iptv_output_aco_rank_r06_10648.json |
| r07 | 607 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 10665 | france_iptv_output_aco_rank_r07_10665.json |
| r08 | 608 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 11008 | france_iptv_output_aco_rank_r08_11008.json |
| r09 | 609 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 10810 | france_iptv_output_aco_rank_r09_10810.json |
| r10 | 610 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 11180 | france_iptv_output_aco_rank_r10_11180.json |

</details>

<details>
<summary><strong>germany_tv</strong> - 10 runs, best score 1553 (r01)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **r01** | **701** | **12** | **10** | **1** | **2** | **0.15** | **10** | **0.8** | **0.5** | **1553** | **germany_tv_output_aco_rank_r01_1553.json** |
| r02 | 702 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 1538 | germany_tv_output_aco_rank_r02_1538.json |
| r03 | 703 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 1538 | germany_tv_output_aco_rank_r03_1538.json |
| r04 | 704 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 1548 | germany_tv_output_aco_rank_r04_1548.json |
| r05 | 705 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 1548 | germany_tv_output_aco_rank_r05_1548.json |
| r06 | 706 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 1538 | germany_tv_output_aco_rank_r06_1538.json |
| r07 | 707 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 1538 | germany_tv_output_aco_rank_r07_1538.json |
| r08 | 708 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 1538 | germany_tv_output_aco_rank_r08_1538.json |
| r09 | 709 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 1533 | germany_tv_output_aco_rank_r09_1553.json |
| r10 | 710 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 1538 | germany_tv_output_aco_rank_r10_1538.json |

</details>

<details>
<summary><strong>kosovo_tv</strong> - 10 runs, best score 2572 (r01)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **r01** | **801** | **12** | **10** | **1** | **2** | **0.15** | **10** | **0.8** | **0.5** | **2572** | **kosovo_tv_output_aco_rank_r01_2572.json** |
| r02 | 802 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r02_2572.json |
| r03 | 803 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r03_2572.json |
| r04 | 804 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r04_2572.json |
| r05 | 805 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r05_2572.json |
| r06 | 806 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r06_2572.json |
| r07 | 807 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r07_2572.json |
| r08 | 808 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r08_2572.json |
| r09 | 809 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 2572 | kosovo_tv_output_aco_rank_r09_2572.json |
| r10 | 810 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 2572 | kosovo_tv_output_aco_rank_r10_2572.json |

</details>

<details>
<summary><strong>netherlands_tv</strong> - 10 runs, best score 2613 (r03)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 901 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2608 | netherlands_tv_output_aco_rank_r01_2608.json |
| r02 | 902 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2608 | netherlands_tv_output_aco_rank_r02_2608.json |
| **r03** | **903** | **16** | **10** | **1** | **2** | **0.15** | **10** | **0.8** | **0.5** | **2613** | **netherlands_tv_output_aco_rank_r03_2613.json** |
| r04 | 904 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2608 | netherlands_tv_output_aco_rank_r04_2608.json |
| r05 | 905 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2613 | netherlands_tv_output_aco_rank_r05_2613.json |
| r06 | 906 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2613 | netherlands_tv_output_aco_rank_r06_2613.json |
| r07 | 907 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2608 | netherlands_tv_output_aco_rank_r07_2608.json |
| r08 | 908 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 2608 | netherlands_tv_output_aco_rank_r08_2608.json |
| r09 | 909 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 2608 | netherlands_tv_output_aco_rank_r09_2608.json |
| r10 | 910 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 2608 | netherlands_tv_output_aco_rank_r10_2608.json |

</details>

<details>
<summary><strong>singapore_pw</strong> - 10 runs, best score 7152 (r04)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 1001 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 7077 | singapore_pw_output_aco_rank_r01_7077.json |
| r02 | 1002 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6847 | singapore_pw_output_aco_rank_r02_6847.json |
| r03 | 1003 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6823 | singapore_pw_output_aco_rank_r03_6823.json |
| **r04** | **1004** | **12** | **10** | **1.2** | **2** | **0.15** | **10** | **0.8** | **0.5** | **7152** | **singapore_pw_output_aco_rank_r04_7152.json** |
| r05 | 1005 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6823 | singapore_pw_output_aco_rank_r05_6823.json |
| r06 | 1006 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6867 | singapore_pw_output_aco_rank_r06_6867.json |
| r07 | 1007 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6849 | singapore_pw_output_aco_rank_r07_6849.json |
| r08 | 1008 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 7079 | singapore_pw_output_aco_rank_r08_7079.json |
| r09 | 1009 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 7141 | singapore_pw_output_aco_rank_r09_7141.json |
| r10 | 1010 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 7097 | singapore_pw_output_aco_rank_r10_7097.json |

</details>

<details>
<summary><strong>spain_iptv</strong> - 10 runs, best score 6727 (r10)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 1101 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6650 | spain_iptv_output_aco_rank_r01_6650.json |
| r02 | 1102 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6616 | spain_iptv_output_aco_rank_r02_6616.json |
| r03 | 1103 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6616 | spain_iptv_output_aco_rank_r03_6616.json |
| r04 | 1104 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6616 | spain_iptv_output_aco_rank_r04_6616.json |
| r05 | 1105 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6689 | spain_iptv_output_aco_rank_r05_6689.json |
| r06 | 1106 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6720 | spain_iptv_output_aco_rank_r06_6720.json |
| r07 | 1107 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 6704 | spain_iptv_output_aco_rank_r07_6704.json |
| r08 | 1108 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 6628 | spain_iptv_output_aco_rank_r08_6628.json |
| r09 | 1109 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 6706 | spain_iptv_output_aco_rank_r09_6706.json |
| **r10** | **1110** | **14** | **10** | **1.3** | **2** | **0.15** | **10** | **0.85** | **0.7** | **6727** | **spain_iptv_output_aco_rank_r10_6727.json** |

</details>

<details>
<summary><strong>toy</strong> - 10 runs, best score 360 (r01)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **r01** | **1201** | **12** | **10** | **1** | **2** | **0.15** | **10** | **0.8** | **0.5** | **360** | **toy_output_aco_rank_r01_360.json** |
| r02 | 1202 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r02_360.json |
| r03 | 1203 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r03_360.json |
| r04 | 1204 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r04_360.json |
| r05 | 1205 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r05_360.json |
| r06 | 1206 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r06_360.json |
| r07 | 1207 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r07_360.json |
| r08 | 1208 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r08_360.json |
| r09 | 1209 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 360 | toy_output_aco_rank_r09_360.json |
| r10 | 1210 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 360 | toy_output_aco_rank_r10_360.json |

</details>

<details>
<summary><strong>uk_iptv</strong> - 10 runs, best score 12699 (r10)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 1301 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12176 | uk_iptv_output_aco_rank_r01_12176.json |
| r02 | 1302 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12060 | uk_iptv_output_aco_rank_r02_12060.json |
| r03 | 1303 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12314 | uk_iptv_output_aco_rank_r03_12314.json |
| r04 | 1304 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12519 | uk_iptv_output_aco_rank_r04_12519.json |
| r05 | 1305 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12519 | uk_iptv_output_aco_rank_r05_12519.json |
| r06 | 1306 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12519 | uk_iptv_output_aco_rank_r06_12519.json |
| r07 | 1307 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 12364 | uk_iptv_output_aco_rank_r07_12364.json |
| r08 | 1308 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 12373 | uk_iptv_output_aco_rank_r08_12373.json |
| r09 | 1309 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 12674 | uk_iptv_output_aco_rank_r09_12674.json |
| **r10** | **1310** | **14** | **10** | **1.3** | **2** | **0.15** | **10** | **0.85** | **0.7** | **12699** | **uk_iptv_output_aco_rank_r10_12699.json** |

</details>

<details>
<summary><strong>uk_tv</strong> - 10 runs, best score 2202 (r09)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 1401 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r01_2197.json |
| r02 | 1402 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r02_2197.json |
| r03 | 1403 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r03_2197.json |
| r04 | 1404 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r04_2197.json |
| r05 | 1405 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r05_2197.json |
| r06 | 1406 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r06_2197.json |
| r07 | 1407 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r07_2197.json |
| r08 | 1408 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 2197 | uk_tv_output_aco_rank_r08_2197.json |
| **r09** | **1409** | **14** | **10** | **1.3** | **2** | **0.15** | **12** | **0.8** | **0.5** | **2202** | **uk_tv_output_aco_rank_r09_2202.json** |
| r10 | 1410 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.85 | 0.7 | 2197 | uk_tv_output_aco_rank_r10_2197.json |

</details>

<details>
<summary><strong>usa_tv</strong> - 10 runs, best score 3575 (r10)</summary>

| Run | Seed | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory | Score | Output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r01 | 1501 | 12 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3569 | usa_tv_output_aco_rank_r01_3569.json |
| r02 | 1502 | 14 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3569 | usa_tv_output_aco_rank_r02_3569.json |
| r03 | 1503 | 16 | 10 | 1 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3569 | usa_tv_output_aco_rank_r03_3569.json |
| r04 | 1504 | 12 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3573 | usa_tv_output_aco_rank_r04_3573.json |
| r05 | 1505 | 14 | 10 | 1.2 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3573 | usa_tv_output_aco_rank_r05_3573.json |
| r06 | 1506 | 14 | 10 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3573 | usa_tv_output_aco_rank_r06_3573.json |
| r07 | 1507 | 14 | 12 | 1.3 | 2 | 0.15 | 10 | 0.8 | 0.5 | 3573 | usa_tv_output_aco_rank_r07_3573.json |
| r08 | 1508 | 14 | 10 | 1.3 | 2 | 0.1 | 10 | 0.8 | 0.5 | 3573 | usa_tv_output_aco_rank_r08_3573.json |
| r09 | 1509 | 14 | 10 | 1.3 | 2 | 0.15 | 12 | 0.8 | 0.5 | 3573 | usa_tv_output_aco_rank_r09_3573.json |
| **r10** | **1510** | **14** | **10** | **1.3** | **2** | **0.15** | **10** | **0.85** | **0.7** | **3575** | **usa_tv_output_aco_rank_r10_3575.json** |

</details>

## Përmbledhje e rezultateve më të mira ACO

| Instance | Ekzekutimet | Ekzekutimi më i mirë | Rezultati më i mirë | Parametrat kryesorë |
|---|---:|---|---:|---|
| australia_iptv | 12 | r10 | 4833 | ants=14, iterations=10, alpha=1.3, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| canada_pw | 10 | r02 | 5972 | ants=14, iterations=10, alpha=1, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| china_pw | 10 | r07 | 2830 | ants=12, iterations=10, alpha=1.3, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| croatia_tv | 10 | r01 | 2203 | ants=12, iterations=10, alpha=1, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| france_iptv | 10 | r05 | 11417 | ants=14, iterations=10, alpha=1.2, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| germany_tv | 10 | r01 | 1553 | ants=12, iterations=10, alpha=1, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| kosovo_tv | 10 | r01 | 2572 | ants=12, iterations=10, alpha=1, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| netherlands_tv | 10 | r03 | 2613 | ants=16, iterations=10, alpha=1, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| singapore_pw | 10 | r04 | 7152 | ants=12, iterations=10, alpha=1.2, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| spain_iptv | 10 | r10 | 6727 | ants=14, iterations=10, alpha=1.3, beta=2, rho=0.15, candidate_cap=10, exploitation=0.85, memory=0.7 |
| toy | 10 | r01 | 360 | ants=12, iterations=10, alpha=1, beta=2, rho=0.15, candidate_cap=10, exploitation=0.8, memory=0.5 |
| uk_iptv | 10 | r10 | 12699 | ants=14, iterations=10, alpha=1.3, beta=2, rho=0.15, candidate_cap=10, exploitation=0.85, memory=0.7 |
| uk_tv | 10 | r09 | 2202 | ants=14, iterations=10, alpha=1.3, beta=2, rho=0.15, candidate_cap=12, exploitation=0.8, memory=0.5 |
| usa_tv | 10 | r10 | 3575 | ants=14, iterations=10, alpha=1.3, beta=2, rho=0.15, candidate_cap=10, exploitation=0.85, memory=0.7 |

## Rezultatet ACO me Local Search

Rezultatet në këtë seksion janë marrë nga output-et me emër `aco_localsearch_rank`. Këto rezultate përdorin `elite carryover` dhe `weakest-window ACO local search`.

Për arsye performance, `uk_iptv` dhe `usa_tv` nuk u përfshinë në këtë raund final të local search, sepse ekzekutimet morën shumë kohë. Për instancat e tjera u përdor e njëjta matricë parametrash `r11-r22`.

<details>
<summary><strong>australia_iptv</strong> - 12 runs, best score 4890 (r20)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 4732 | australia_iptv_output_aco_localsearch_rank_r11_4732.json |
| r12 | 4835 | australia_iptv_output_aco_localsearch_rank_r12_4835.json |
| r13 | 4692 | australia_iptv_output_aco_localsearch_rank_r13_4692.json |
| r14 | 4707 | australia_iptv_output_aco_localsearch_rank_r14_4707.json |
| r15 | 4719 | australia_iptv_output_aco_localsearch_rank_r15_4719.json |
| r16 | 4675 | australia_iptv_output_aco_localsearch_rank_r16_4675.json |
| r17 | 4655 | australia_iptv_output_aco_localsearch_rank_r17_4655.json |
| r18 | 4597 | australia_iptv_output_aco_localsearch_rank_r18_4597.json |
| r19 | 4735 | australia_iptv_output_aco_localsearch_rank_r19_4735.json |
| **r20** | **4890** | **australia_iptv_output_aco_localsearch_rank_r20_4890.json** |
| r21 | 4877 | australia_iptv_output_aco_localsearch_rank_r21_4877.json |
| r22 | 4693 | australia_iptv_output_aco_localsearch_rank_r22_4693.json |

</details>

<details>
<summary><strong>canada_pw</strong> - 12 runs, best score 5938 (r19)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 5799 | canada_pw_output_aco_localsearch_rank_r11_5799.json |
| r12 | 5935 | canada_pw_output_aco_localsearch_rank_r12_5935.json |
| r13 | 5877 | canada_pw_output_aco_localsearch_rank_r13_5877.json |
| r14 | 5909 | canada_pw_output_aco_localsearch_rank_r14_5909.json |
| r15 | 5878 | canada_pw_output_aco_localsearch_rank_r15_5878.json |
| r16 | 5878 | canada_pw_output_aco_localsearch_rank_r16_5878.json |
| r17 | 5862 | canada_pw_output_aco_localsearch_rank_r17_5862.json |
| r18 | 5891 | canada_pw_output_aco_localsearch_rank_r18_5891.json |
| **r19** | **5938** | **canada_pw_output_aco_localsearch_rank_r19_5938.json** |
| r20 | 5913 | canada_pw_output_aco_localsearch_rank_r20_5913.json |
| r21 | 5916 | canada_pw_output_aco_localsearch_rank_r21_5916.json |
| r22 | 5845 | canada_pw_output_aco_localsearch_rank_r22_5845.json |

</details>

<details>
<summary><strong>china_pw</strong> - 12 runs, best score 2837 (r13)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 2818 | china_pw_output_aco_localsearch_rank_r11_2818.json |
| r12 | 2835 | china_pw_output_aco_localsearch_rank_r12_2835.json |
| **r13** | **2837** | **china_pw_output_aco_localsearch_rank_r13_2837.json** |
| r14 | 2835 | china_pw_output_aco_localsearch_rank_r14_2835.json |
| r15 | 2835 | china_pw_output_aco_localsearch_rank_r15_2835.json |
| r16 | 2835 | china_pw_output_aco_localsearch_rank_r16_2835.json |
| r17 | 2835 | china_pw_output_aco_localsearch_rank_r17_2835.json |
| r18 | 2829 | china_pw_output_aco_localsearch_rank_r18_2829.json |
| r19 | 2829 | china_pw_output_aco_localsearch_rank_r19_2829.json |
| r20 | 2823 | china_pw_output_aco_localsearch_rank_r20_2823.json |
| r21 | 2795 | china_pw_output_aco_localsearch_rank_r21_2795.json |
| r22 | 2811 | china_pw_output_aco_localsearch_rank_r22_2811.json |

</details>

<details>
<summary><strong>croatia_tv</strong> - 12 runs, best score 2203 (r11-r20)</summary>

| Run | Score | Output |
|---|---:|---|
| **r11** | **2203** | **croatia_tv_output_aco_localsearch_rank_r11_2203.json** |
| r12 | 2203 | croatia_tv_output_aco_localsearch_rank_r12_2203.json |
| r13 | 2203 | croatia_tv_output_aco_localsearch_rank_r13_2203.json |
| r14 | 2203 | croatia_tv_output_aco_localsearch_rank_r14_2203.json |
| r15 | 2203 | croatia_tv_output_aco_localsearch_rank_r15_2203.json |
| r16 | 2203 | croatia_tv_output_aco_localsearch_rank_r16_2203.json |
| r17 | 2203 | croatia_tv_output_aco_localsearch_rank_r17_2203.json |
| r18 | 2203 | croatia_tv_output_aco_localsearch_rank_r18_2203.json |
| r19 | 2203 | croatia_tv_output_aco_localsearch_rank_r19_2203.json |
| r20 | 2203 | croatia_tv_output_aco_localsearch_rank_r20_2203.json |
| r21 | 2199 | croatia_tv_output_aco_localsearch_rank_r21_2199.json |
| r22 | 2199 | croatia_tv_output_aco_localsearch_rank_r22_2199.json |

</details>

<details>
<summary><strong>france_iptv</strong> - 12 runs, best score 11026 (r14)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 10942 | france_iptv_output_aco_localsearch_rank_r11_10942.json |
| r12 | 10681 | france_iptv_output_aco_localsearch_rank_r12_10681.json |
| r13 | 10689 | france_iptv_output_aco_localsearch_rank_r13_10689.json |
| **r14** | **11026** | **france_iptv_output_aco_localsearch_rank_r14_11026.json** |
| r15 | 10857 | france_iptv_output_aco_localsearch_rank_r15_10857.json |
| r16 | 10883 | france_iptv_output_aco_localsearch_rank_r16_10883.json |
| r17 | 10883 | france_iptv_output_aco_localsearch_rank_r17_10883.json |
| r18 | 10883 | france_iptv_output_aco_localsearch_rank_r18_10883.json |
| r19 | 10883 | france_iptv_output_aco_localsearch_rank_r19_10883.json |
| r20 | 10880 | france_iptv_output_aco_localsearch_rank_r20_10880.json |
| r21 | 10677 | france_iptv_output_aco_localsearch_rank_r21_10677.json |
| r22 | 10864 | france_iptv_output_aco_localsearch_rank_r22_10864.json |

</details>

<details>
<summary><strong>germany_tv</strong> - 12 runs, best score 1558 (r12)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 1518 | germany_tv_output_aco_localsearch_rank_r11_1518.json |
| **r12** | **1558** | **germany_tv_output_aco_localsearch_rank_r12_1558.json** |
| r13 | 1500 | germany_tv_output_aco_localsearch_rank_r13_1500.json |
| r14 | 1533 | germany_tv_output_aco_localsearch_rank_r14_1533.json |
| r15 | 1548 | germany_tv_output_aco_localsearch_rank_r15_1548.json |
| r16 | 1548 | germany_tv_output_aco_localsearch_rank_r16_1548.json |
| r17 | 1533 | germany_tv_output_aco_localsearch_rank_r17_1533.json |
| r18 | 1548 | germany_tv_output_aco_localsearch_rank_r18_1548.json |
| r19 | 1533 | germany_tv_output_aco_localsearch_rank_r19_1533.json |
| r20 | 1500 | germany_tv_output_aco_localsearch_rank_r20_1500.json |
| r21 | 1548 | germany_tv_output_aco_localsearch_rank_r21_1548.json |
| r22 | 1548 | germany_tv_output_aco_localsearch_rank_r22_1548.json |

</details>

<details>
<summary><strong>kosovo_tv</strong> - 12 runs, best score 2577 (r12)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 2572 | kosovo_tv_output_aco_localsearch_rank_r11_2572.json |
| **r12** | **2577** | **kosovo_tv_output_aco_localsearch_rank_r12_2577.json** |
| r13 | 2573 | kosovo_tv_output_aco_localsearch_rank_r13_2573.json |
| r14 | 2573 | kosovo_tv_output_aco_localsearch_rank_r14_2573.json |
| r15 | 2573 | kosovo_tv_output_aco_localsearch_rank_r15_2573.json |
| r16 | 2573 | kosovo_tv_output_aco_localsearch_rank_r16_2573.json |
| r17 | 2572 | kosovo_tv_output_aco_localsearch_rank_r17_2572.json |
| r18 | 2572 | kosovo_tv_output_aco_localsearch_rank_r18_2572.json |
| r19 | 2572 | kosovo_tv_output_aco_localsearch_rank_r19_2572.json |
| r20 | 2573 | kosovo_tv_output_aco_localsearch_rank_r20_2573.json |
| r21 | 2572 | kosovo_tv_output_aco_localsearch_rank_r21_2572.json |
| r22 | 2572 | kosovo_tv_output_aco_localsearch_rank_r22_2572.json |

</details>

<details>
<summary><strong>netherlands_tv</strong> - 12 runs, best score 2620 (r19)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 2613 | netherlands_tv_output_aco_localsearch_rank_r11_2613.json |
| r12 | 2615 | netherlands_tv_output_aco_localsearch_rank_r12_2615.json |
| r13 | 2608 | netherlands_tv_output_aco_localsearch_rank_r13_2608.json |
| r14 | 2608 | netherlands_tv_output_aco_localsearch_rank_r14_2608.json |
| r15 | 2610 | netherlands_tv_output_aco_localsearch_rank_r15_2610.json |
| r16 | 2610 | netherlands_tv_output_aco_localsearch_rank_r16_2610.json |
| r17 | 2615 | netherlands_tv_output_aco_localsearch_rank_r17_2615.json |
| r18 | 2608 | netherlands_tv_output_aco_localsearch_rank_r18_2608.json |
| **r19** | **2620** | **netherlands_tv_output_aco_localsearch_rank_r19_2620.json** |
| r20 | 2610 | netherlands_tv_output_aco_localsearch_rank_r20_2610.json |
| r21 | 2608 | netherlands_tv_output_aco_localsearch_rank_r21_2608.json |
| r22 | 2608 | netherlands_tv_output_aco_localsearch_rank_r22_2608.json |

</details>

<details>
<summary><strong>singapore_pw</strong> - 12 runs, best score 7076 (r22)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 6884 | singapore_pw_output_aco_localsearch_rank_r11_6884.json |
| r12 | 6903 | singapore_pw_output_aco_localsearch_rank_r12_6903.json |
| r13 | 6861 | singapore_pw_output_aco_localsearch_rank_r13_6861.json |
| r14 | 6847 | singapore_pw_output_aco_localsearch_rank_r14_6847.json |
| r15 | 6925 | singapore_pw_output_aco_localsearch_rank_r15_6925.json |
| r16 | 6932 | singapore_pw_output_aco_localsearch_rank_r16_6932.json |
| r17 | 6913 | singapore_pw_output_aco_localsearch_rank_r17_6913.json |
| r18 | 6913 | singapore_pw_output_aco_localsearch_rank_r18_6913.json |
| r19 | 6953 | singapore_pw_output_aco_localsearch_rank_r19_6953.json |
| r20 | 6824 | singapore_pw_output_aco_localsearch_rank_r20_6824.json |
| r21 | 6810 | singapore_pw_output_aco_localsearch_rank_r21_6810.json |
| **r22** | **7076** | **singapore_pw_output_aco_localsearch_rank_r22_7076.json** |

</details>

<details>
<summary><strong>spain_iptv</strong> - 12 runs, best score 6871 (r20)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 6672 | spain_iptv_output_aco_localsearch_rank_r11_6672.json |
| r12 | 6687 | spain_iptv_output_aco_localsearch_rank_r12_6687.json |
| r13 | 6713 | spain_iptv_output_aco_localsearch_rank_r13_6713.json |
| r14 | 6720 | spain_iptv_output_aco_localsearch_rank_r14_6720.json |
| r15 | 6745 | spain_iptv_output_aco_localsearch_rank_r15_6745.json |
| r16 | 6684 | spain_iptv_output_aco_localsearch_rank_r16_6684.json |
| r17 | 6800 | spain_iptv_output_aco_localsearch_rank_r17_6800.json |
| r18 | 6783 | spain_iptv_output_aco_localsearch_rank_r18_6783.json |
| r19 | 6782 | spain_iptv_output_aco_localsearch_rank_r19_6782.json |
| **r20** | **6871** | **spain_iptv_output_aco_localsearch_rank_r20_6871.json** |
| r21 | 6773 | spain_iptv_output_aco_localsearch_rank_r21_6773.json |
| r22 | 6730 | spain_iptv_output_aco_localsearch_rank_r22_6730.json |

</details>

<details>
<summary><strong>toy</strong> - 12 runs, best score 360 (r11-r22)</summary>

| Run | Score | Output |
|---|---:|---|
| **r11** | **360** | **toy_output_aco_localsearch_rank_r11_360.json** |
| r12 | 360 | toy_output_aco_localsearch_rank_r12_360.json |
| r13 | 360 | toy_output_aco_localsearch_rank_r13_360.json |
| r14 | 360 | toy_output_aco_localsearch_rank_r14_360.json |
| r15 | 360 | toy_output_aco_localsearch_rank_r15_360.json |
| r16 | 360 | toy_output_aco_localsearch_rank_r16_360.json |
| r17 | 360 | toy_output_aco_localsearch_rank_r17_360.json |
| r18 | 360 | toy_output_aco_localsearch_rank_r18_360.json |
| r19 | 360 | toy_output_aco_localsearch_rank_r19_360.json |
| r20 | 360 | toy_output_aco_localsearch_rank_r20_360.json |
| r21 | 360 | toy_output_aco_localsearch_rank_r21_360.json |
| r22 | 360 | toy_output_aco_localsearch_rank_r22_360.json |

</details>

<details>
<summary><strong>uk_tv</strong> - 12 runs, best score 2209 (r18)</summary>

| Run | Score | Output |
|---|---:|---|
| r11 | 2201 | uk_tv_output_aco_localsearch_rank_r11_2201.json |
| r12 | 2202 | uk_tv_output_aco_localsearch_rank_r12_2202.json |
| r13 | 2202 | uk_tv_output_aco_localsearch_rank_r13_2202.json |
| r14 | 2202 | uk_tv_output_aco_localsearch_rank_r14_2202.json |
| r15 | 2202 | uk_tv_output_aco_localsearch_rank_r15_2202.json |
| r16 | 2202 | uk_tv_output_aco_localsearch_rank_r16_2202.json |
| r17 | 2202 | uk_tv_output_aco_localsearch_rank_r17_2202.json |
| **r18** | **2209** | **uk_tv_output_aco_localsearch_rank_r18_2209.json** |
| r19 | 2209 | uk_tv_output_aco_localsearch_rank_r19_2209.json |
| r20 | 2202 | uk_tv_output_aco_localsearch_rank_r20_2202.json |
| r21 | 2209 | uk_tv_output_aco_localsearch_rank_r21_2209.json |
| r22 | 2209 | uk_tv_output_aco_localsearch_rank_r22_2209.json |

</details>

## Përmbledhje e ACO me Local Search

| Instance | Best ACO | Best ACO + Local Search | Ndryshimi |
|---|---:|---:|---:|
| australia_iptv | 4833 | 4890 | +57 |
| canada_pw | 5972 | 5938 | -34 |
| china_pw | 2830 | 2837 | +7 |
| croatia_tv | 2203 | 2203 | 0 |
| france_iptv | 11417 | 11026 | -391 |
| germany_tv | 1553 | 1558 | +5 |
| kosovo_tv | 2572 | 2577 | +5 |
| netherlands_tv | 2613 | 2620 | +7 |
| singapore_pw | 7152 | 7076 | -76 |
| spain_iptv | 6727 | 6871 | +144 |
| toy | 360 | 360 | 0 |
| uk_tv | 2202 | 2209 | +7 |

Local search nuk garanton gjithmonë rezultat më të lartë se ACO pa local search, sepse ai rindërton vetëm pjesën pas weakest-window dhe pranon vetëm nëse kandidati lokal e kalon zgjidhjen e atij run-i. Megjithatë, në disa instanca ai e gjeti rezultat më të mirë se ACO-ja e mëparshme, sidomos te `australia_iptv`, `spain_iptv`, `netherlands_tv`, `germany_tv`, `kosovo_tv` dhe `uk_tv`.

## Matrica e Parametrave dhe Mesatarizimi

Për raundin final u përdor e njëjta matricë parametrash për instancat e ekzekutuara. Kjo e bën krahasimin më të drejtë, sepse secila instancë provohet me të njëjtat konfigurime `r11-r22`; ndryshon vetëm `seed`, i cili bazohet në instance.

| Run | Ants | Iter | Alpha | Beta | Rho | Cap | Exploit | Memory |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| r11 | 12 | 10 | 1.3 | 2.0 | 0.10 | 10 | 0.80 | 0.50 |
| r12 | 14 | 10 | 1.0 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r13 | 14 | 10 | 1.3 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r14 | 16 | 10 | 1.3 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r15 | 14 | 12 | 1.3 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r16 | 16 | 12 | 1.3 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r17 | 14 | 10 | 1.4 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r18 | 16 | 10 | 1.4 | 2.0 | 0.15 | 10 | 0.80 | 0.50 |
| r19 | 14 | 10 | 1.3 | 2.0 | 0.10 | 10 | 0.80 | 0.50 |
| r20 | 14 | 10 | 1.3 | 2.0 | 0.15 | 12 | 0.80 | 0.50 |
| r21 | 14 | 10 | 1.3 | 2.0 | 0.15 | 10 | 0.85 | 0.70 |
| r22 | 16 | 10 | 1.3 | 2.0 | 0.15 | 10 | 0.85 | 0.70 |

Mesatarja e matricës së parametrave është:

| Parametri | Mesatarja |
|---|---:|
| Ants | 14.50 |
| Iterations | 10.33 |
| Alpha | 1.29 |
| Beta | 2.00 |
| Rho | 0.14 |
| Candidate cap | 10.17 |
| Exploitation probability | 0.81 |
| Memory strength | 0.53 |

## Ekzekutimi

Ekzekutimi bazë me zgjedhje interaktive të input file:

```bash
python main.py
```

Nëse komanda `python` nuk funksionon në Windows, mund të përdoret:

```bash
py main.py
```

Ekzekutim me input të caktuar:

```bash
python main.py -i data/input/kosovo_tv_input.json
```

Ekzekutim ACO:

```bash
python main.py --algorithm aco -i data/input/kosovo_tv_input.json
```

Ekzekutim ACO me tuning:

```bash
python main.py --algorithm aco -i data/input/kosovo_tv_input.json -o data/output_aco_tuning/kosovo --run-id r01 --ants 12 --iterations 10 --alpha 1.0 --beta 2.0 --rho 0.15 --candidate-cap 10 --exploitation-prob 0.80 --memory-strength 0.50 --seed 801 --verbose
```

## Output-et

Output-et ruhen si JSON dhe përmbajnë listën e programeve të planifikuara:

```json
{
  "scheduled_programs": [
    {
      "program_id": "...",
      "channel_id": 0,
      "start": 540,
      "end": 600
    }
  ]
}
```

Folderët kryesorë të rezultateve:

- `data/output`: rezultate bazë ose të mëhershme
- `data/output_randomness`: rezultate të Beam Search me randomness
- `data/output_aco_tuning`: rezultate të ACO dhe eksperimenteve të tuning

## Struktura e Projektit

```text
data/input/                       Input JSON files
data/output/                      Output-et bazë
data/output_randomness/           Output-et e Beam Search me randomness
data/output_aco_tuning/           Output-et e ACO tuning
models/                           Modelet kryesore të të dhënave
parser/                           Leximi dhe zgjedhja e input file
scheduler/beam_search_scheduler.py
scheduler/rank_based_aco_scheduler.py
serializer/serializer.py
main.py                           Entry point i projektit
```

## Përmbledhje

Zgjidhja finale përfshin dy drejtime kryesore optimizimi:

- `Beam Search` me randomness të kontrolluar, i cili eksploron alternativa të afërta me kandidatët më të mirë.
- `Rank-based ACO`, ku ants ndërtojnë zgjidhje valide, përditësojnë feromonin sipas rankut, përdorin time-transition memory dhe mund të tunohen përmes parametrave të CLI.

Këto ndryshime e bëjnë projektin më fleksibil për eksperimente dhe më të mbrojtshëm teorikisht, sepse optimizimi nuk bazohet vetëm në randomness, por në heuristikë, feromon, rank-based reinforcement, memory dhe tuning të parametrave.
