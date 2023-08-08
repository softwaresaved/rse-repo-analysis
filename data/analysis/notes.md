# Notes on RSE repo analysis

**WORK IN PROGRESS.**

## Dataset

### Collection

1. Crawled [23 ePrints repositories](../eprints_repos.txt) for any PDFs dated 2010 until date of analysis (June 2023) ([script](../../eprints/parse_eprints.py)).
2. Parsed every available PDF and searched full text for GitHub links (RegEx pattern `"(?P<url>https?://(www\.)?github\.com[^\s]+)"`) ([script](../../eprints/parse_pdfs.py)). 
3. Matched the detected links to existing GitHub repositories ([script](../../eprints/clean_eprints_links.py)).
4. Used GitHub API to collect a variety of info about each of the repositories ([scripts](../../github/)).

### Structure

[GitHub links in ePrints](./cleaned_links/joined.csv):
- `eprints_repo`: ePrints repository name
- `title`: publication title
- `author_for_reference`: one of the listed authors
- `date`: date given for ePrints publication
- `year`: year extracted from `date`
- `pdf_url`: URL of publication PDF
- `page_no`: number of page where GitHub link was found
- `domain_url`: GitHub link
- `pattern_cleaned_url`: post-processed GitHub link (added RegEx matching)
- `github_user_cleaned_url`: GitHub link matched against an existing repository

[GitHub repository metadata](./metadata.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `archived`: whether the repository is archived
- `created_at`: date of repository creation
- `has_wiki`: whether the repository has a wiki
- `has_pages`: whether the repository has GitHub pages

[GitHub repository contents](./contents.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `license`: license type as recognised by GitHub API ([more info](https://docs.github.com/en/rest/licenses/licenses?apiVersion=2022-11-28))
- `readme_size`: byte size of README file
- `readme_path`: path to README file (usually `./README.md`)
- `readme_emojis`: number of emojis used in the README file
- `contributing_size`: size of `CONTRIBUTING.md`
- `citation_added`: date that a `CITATION.cff` file was added
- `contributing_added`: date that a `CONTRIBUTING.md` file was added

[GitHub repository contributions](./contributions.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `author`: user ID of commit author
- `week_co`: date of start a week
- `commits`: number of commits the author made in that week

[GitHub repository issues](./issues.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `state`: issue state at date of crawling (June 2023)
- `created_at`: date of issue creation
- `user`: user ID of issue author
- `closed_at`: date the issue was closed (can be empty)
- `closed_by`: user ID of user who closed the issue (can be empty)

[GitHub repository README evolution](./readme_history.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `readme_path`: path to README file (usually `./README.md`)
- `author_date`: date of commit to README
- `added_headings`: new headings
- `deleted_headings`: removed headings
- `added_cites`: new citation info (DOI etc.)

[GitHub repository stars](./stars.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `date`: date of star
- `user`: user ID of user that starred the repository

[GitHub repository forks](./forks.csv):
- `github_user_cleaned_url`: repository ID (format `<user>/<repo_name>`)
- `date`: date of fork
- `user`: user ID of user that forked the repository

## Analysis

### ePrints

<img src="./overall/github_in_eprints.png" width="600"/>

<img src="./overall/avg_github_in_eprints.png" width="600"/>

<img src="./overall/min_one_github_in_eprints.png" width="800"/>

### GitHub

<img src="./overall/overall.png" width="800"/>

#### Repository timelines

Timelines were plotted for each repository mentioned on the first two pages of the publication that was manually verified as the code for this publication ("true positives"). The upper plot shows how users interact with repository issues. We take a rolling window approach, where a user is considered to be opening issues up until 12 weeks after opening an issue, similarly for closing issues. The middle plot shows the same analysis for contributions (i.e. commits). The last plot shows summary statistics over time, such as forks, stars and contributor team size. Highlights are depicted with little triangles.

We can roughly separate the repositories into three groups: 
- one-person repositories, where only one user makes contributions and interacts with issues (30 repositories)
- high-interest repositories, where many (>5 I think, this was decided visually) users contribute and interact with issues (5 repositories)
- everything in between (23 repositories).

Of course, this separation disregards that some repositories are developed by teams rather than just one person and that this might be the reason for the "high interest", but it's just a starting point, not a result.

##### One-person repositories

<img src="./repo_timelines/one_user/andrewtarzia-cage_datasets.png" width="800"/>
<img src="./repo_timelines/one_user/AshwathyTR-IDN-Sum.png" width="800"/>
<img src="./repo_timelines/one_user/asolimando-logmap-conservativity.png" width="800"/>
<img src="./repo_timelines/one_user/bernuly-VCSimulinkTlbx.png" width="800"/>
<img src="./repo_timelines/one_user/cylammarco-ASPIRED-example.png" width="800"/>
<img src="./repo_timelines/one_user/cylammarco-bhtomspec.png" width="800"/>
<img src="./repo_timelines/one_user/eghbal11-Eghbal.png" width="800"/>
<img src="./repo_timelines/one_user/ethanwharris-foveated-convolutions.png" width="800"/>
<img src="./repo_timelines/one_user/eugenesiow-piotre.png" width="800"/>
<img src="./repo_timelines/one_user/fcampelo-epitopes.png" width="800"/>
<img src="./repo_timelines/one_user/fcampelo-OrgSpec-paper.png" width="800"/>
<img src="./repo_timelines/one_user/gamesbyangelina-danesh.png" width="800"/>
<img src="./repo_timelines/one_user/ilkaza-JPAL-HA.png" width="800"/>
<img src="./repo_timelines/one_user/JAEarly-MILLI.png" width="800"/>
<img src="./repo_timelines/one_user/Katerina-Pap-MA-cont-shiny-app.png" width="800"/>
<img src="./repo_timelines/one_user/lphowell-Geothermal-Modelling.png" width="800"/>
<img src="./repo_timelines/one_user/NabajeetBarman-GamingHDRVideoSET.png" width="800"/>
<img src="./repo_timelines/one_user/oreindt-routes-rumours-ml3.png" width="800"/>
<img src="./repo_timelines/one_user/P-R-McWhirter-pyOsiris.png" width="800"/>
<img src="./repo_timelines/one_user/pbw20-SULISO_manuals.png" width="800"/>
<img src="./repo_timelines/one_user/philgooch-BADREX-Biomedical-Abbreviation-Expander.png" width="800"/>
<img src="./repo_timelines/one_user/SamirNepal-Li_CNN_2022.png" width="800"/>
<img src="./repo_timelines/one_user/sanket0707-GNN-Mixer.png" width="800"/>
<img src="./repo_timelines/one_user/SigmaLabResearch-Visnotate.png" width="800"/>
<img src="./repo_timelines/one_user/sjoudaki-cfhtlens_revisited.png" width="800"/>
<img src="./repo_timelines/one_user/stootaghaj-DEMI.png" width="800"/>
<img src="./repo_timelines/one_user/TGMclustering-TGMclustering.png" width="800"/>
<img src="./repo_timelines/one_user/WavEC-Offshore-Renewables-tokyo-wavec-fowt.png" width="800"/>
<img src="./repo_timelines/one_user/xgfd-ASPG.png" width="800"/>
<img src="./repo_timelines/one_user/xiongbo010-QGCN.png" width="800"/>

##### High-interest repositories

<img src="./repo_timelines/many_users/agentsoz-bdi-abm-integration.png" width="800"/>
<img src="./repo_timelines/many_users/IraKorshunova-folk-rnn.png" width="800"/>
<img src="./repo_timelines/many_users/morriscb-The-wiZZ.png" width="800"/>
<img src="./repo_timelines/many_users/tharindudr-transquest.png" width="800"/>
<img src="./repo_timelines/many_users/ziqizhang-sti.png" width="800"/>

##### In between

<img src="./repo_timelines/inbetween/52North-GEO-label-java.png" width="800"/>
<img src="./repo_timelines/inbetween/brunneis-ilab-erisk-2020.png" width="800"/>
<img src="./repo_timelines/inbetween/CVML-UCLan-FCBFormer.png" width="800"/>
<img src="./repo_timelines/inbetween/ecs-vlc-opponency.png" width="800"/>
<img src="./repo_timelines/inbetween/EPiCS-CamSim.png" width="800"/>
<img src="./repo_timelines/inbetween/epsilonlabs-emf-cbp.png" width="800"/>
<img src="./repo_timelines/inbetween/fcampelo-MOEADr.png" width="800"/>
<img src="./repo_timelines/inbetween/FlorianSteinberg-incone.png" width="800"/>
<img src="./repo_timelines/inbetween/jordan-bird-synthetic-fruit-image-generator.png" width="800"/>
<img src="./repo_timelines/inbetween/lushv-geolabel-service.png" width="800"/>
<img src="./repo_timelines/inbetween/mhinsch-RRGraphs_mini.png" width="800"/>
<img src="./repo_timelines/inbetween/NeuroanatomyAndConnectivity-broca.png" width="800"/>
<img src="./repo_timelines/inbetween/NeuroanatomyAndConnectivity-nki_nilearn.png" width="800"/>
<img src="./repo_timelines/inbetween/PRiME-project-PRiME-Framework.png" width="800"/>
<img src="./repo_timelines/inbetween/prov-suite-prov-sty.png" width="800"/>
<img src="./repo_timelines/inbetween/quitadal-EPINETLAB.png" width="800"/>
<img src="./repo_timelines/inbetween/rOpenHealth-ClinicalCodes.png" width="800"/>
<img src="./repo_timelines/inbetween/SigmaLabResearch-Gaze-Enabled-Histopathology.png" width="800"/>
<img src="./repo_timelines/inbetween/survival-lumc-ValidationCompRisks.png" width="800"/>
<img src="./repo_timelines/inbetween/tstafylakis-Lipreading-ResNet.png" width="800"/>
<img src="./repo_timelines/inbetween/vangiel-WheresTheFellow.png" width="800"/>
<img src="./repo_timelines/inbetween/vraj004-RyR-simulator.png" width="800"/>
<img src="./repo_timelines/inbetween/zdai257-DeepAoANet.png" width="800"/>