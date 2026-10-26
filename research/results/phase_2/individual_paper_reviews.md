# Individual Paper Reviews

Full-text entries examine the cited sections. Limited-access entries are explicitly excluded from the deep-analysis count. Numbers are source-reported and not comparable across datasets.

## P01: RE-RecSys: An End-to-End system for recommending properties in Real-Estate domain

Venkatesh C; Harshit Oberoi; Anil Goyal; Nikhil Sikka, RE-RecSys: An End-to-End system for recommending properties in Real-Estate domain, CODS-COMAD 2024, 2024.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

The system switches among popularity rules, content profiles, and latent factors according to available history. India platform interactions support time-window and weighting comparisons, with MAP and NDCG measuring later engagement. Deployment evidence is a strength, but no independently annotated housing-decision outcome follows from those metrics. For DhakaNest, this is evidence that locality-based hybrids already exist; explicit needs and frozen relevance evaluation need separate justification. The published score cannot be compared numerically with DhakaNest's smaller, differently judged benchmark.

Evidence: [Sections 2.0.1-2.0.5 and 3; Tables 2-3](https://arxiv.org/html/2404.16553v1). Links: RQ1, RQ4, H1, H4A, H4B.

## P02: Recommender Systems in the Real Estate Market-A Survey

Alireza Gharahighehi; Konstantinos Pliakos; Celine Vens, Recommender Systems in the Real Estate Market-A Survey, Applied Sciences 11(16), 7502, 2021.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

The review separates knowledge-based, collaborative, content, multi-criteria, and hybrid approaches rather than treating property search as one algorithmic task. Its tables connect inputs and evaluation choices to primary studies. In particular, its journey-aware references undermine a claim that destination-sensitive housing choice is unprecedented. The corpus is useful for finding comparators, but secondary descriptions cannot replace reading each primary study, and its 2021 coverage cannot establish absence of later methods. DhakaNest should use this taxonomy to describe its design and evaluation limits.

Evidence: [Sections 3-6; Section 4.4; Appendix A](https://pdfs.semanticscholar.org/3d6a/e7ee5627f59a1de3abce5dce9230c1d823c2.pdf). Links: RQ1, RQ2, RQ4, H1, H2, H4B.

## P03: A Recommender System for Cold-start Items: A Case Study in the Real Estate Industry

Qian Zhang; Di Zhang; Jie Lu; Guangquan Zhang; Wei Qu; Mark Cohen, A Recommender System for Cold-start Items: A Case Study in the Real Estate Industry, IEEE ISKE 2019, 1185-1192, 2019.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

One-hot content vectors retrieve users by cosine similarity; a second XGBoost stage estimates interaction probabilities to reduce irrelevant notifications. Australian property subsets and sale/rent scenarios are evaluated against query rules and first-stage retrieval. This directly precedes the idea of separating retrieval and ranking. Its strengths are staged evaluation and explicit cold-item scenarios. Our limitation assessment is that implicit interactions can miss latent housing needs. Its XGBoost role must not be confused with DhakaNest's stored rent estimate.

Evidence: [Sections III-IV; Tables III-VII](https://opus.lib.uts.edu.au/bitstream/10453/148303/2/Domain_ISKE_submit.pdf). Links: RQ1, RQ4, H1, H4A, H4B.

## P04: HomeFinder Revisited: Finding Ideal Homes with Reachability-Centric Multi-Criteria Decision Making

Di Weng; Heming Zhu; Jie Bao; Yu Zheng; Yingcai Wu, HomeFinder Revisited: Finding Ideal Homes with Reachability-Centric Multi-Criteria Decision Making, CHI 2018, 2018.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

ReACH accepts daily routines and reachability requirements, computes trajectory-based reachable regions, and supports filtering and multi-criteria comparison. Its 14-person task study demonstrates usability under tested tasks. It provides stronger precedent for journey-centered housing choice than a generic proximity recommender. Authors report interface-learning and map-comparison difficulties. Our assessment is that task correctness does not establish superiority over the full set of modern rankers. DhakaNest needs a direct conceptual comparison and must explain its simpler routing assumptions and rent-assessment integration without claiming destination-first novelty.

Evidence: [System Architecture; Reachability Model; User Study; Discussion](https://dwe.ng/pdf/reach.pdf). Links: RQ2, RQ3, H2, H3.

## P05: The dynamic HomeFinder: evaluating dynamic queries in a real-estate information exploration system

Christopher Williamson; Ben Shneiderman, The dynamic HomeFinder: evaluating dynamic queries in a real-estate information exploration system, SIGIR 1992, 338-346, 1992.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

Dynamic sliders and linked maps let users refine property searches immediately. Eighteen participants completed counterbalanced tasks using the interface, natural-language queries, and paper listings. Distance markers existed, but were deliberately omitted from the comparison because the controls lacked them. This is a useful fairness lesson: interface information must be matched before attributing a decision benefit to ranking. The study supports controlled task evaluation, while its historical hardware and sample prevent direct prediction of DhakaNest's effect size. Repository deposit date is not the publication year.

Evidence: [Sections 1.2 and 3, User Experiment](https://drum.lib.umd.edu/bitstreams/d1b73c1e-725b-4900-9cca-bd1aad078995/download). Links: RQ3, H3.

## P06: CFRecs: Counterfactual Recommendations on Real Estate User Listing Interaction Graphs

Seyedmasoud Mousavi; Ruomeng Xu; Xiaojing Zhu, CFRecs: Counterfactual Recommendations on Real Estate User Listing Interaction Graphs, arXiv:2602.05861, 2026.

Access: `full_text_examined`. Publication status: `unverified_preprint`.

A graph classifier predicts transactional outcomes and a Graph-VAE proposes sparse changes to listing-user interaction graphs. Experiments use Zillow graphs and compare validity/proximity with random modifications. This offers a different explanation objective from reasons attached to a fixed rental ranking. Our assessment is that improving a classifier's predicted outcome does not establish causal benefit or decision quality. The accessible manuscript contains placeholder conference identifiers; it is retained as a clearly labeled 2026 preprint, with peer review unverified.

Evidence: [Sections 3-5; Table 2](https://arxiv.org/pdf/2602.05861). Links: RQ3, RQ4, H3, H4B.

## P07: Following the Preference, Missing the Optimum: Compliance Without Optimization in AI Housing Recommendation

Hsuan Lo, Following the Preference, Missing the Optimum: Compliance Without Optimization in AI Housing Recommendation, arXiv:2609.10856, 2026.

Access: `full_text_examined`. Publication status: `unverified_preprint`.

The audit enumerates feasible alternatives using rent, bedrooms, and GTFS commute before checking model recommendations for strict dominance. It distinguishes satisfying a constraint from selecting a good feasible option. Results are author-reported experimental evidence, not independently replicated findings. Our assessment is that model-version and synthetic-profile choices limit transfer to Dhaka. The design nevertheless motivates an optional future Pareto diagnostic alongside NDCG and coverage. Such a diagnostic requires a controlled protocol revision and must not be inserted into the frozen Phase 1 metrics silently.

Evidence: [Sections 1-5 and 8; version status page](https://arxiv.org/pdf/2609.10856). Links: RQ1, RQ5, H1, H5.

## P08: Recommender systems in real estate: a systematic review

Carlos Henriquez-Miranda; Jesus Rios-Perez; German Sanchez-Torres, Recommender systems in real estate: a systematic review, Bulletin of Electrical Engineering and Informatics 14(3), 2025.

Access: `abstract_and_metadata_examined`. Publication status: `journal_publication_verified`.

The publisher abstract identifies four recommendation families and highlights sparsity, cold start, and adaptive learning. This establishes topical relevance, but the PDF requests timed out, so screening details, study counts, and comparative findings remain unassessed. Retain as a limited-access reference; it does not count toward the substantive full-text target.

Evidence: [Publisher abstract; PDF retrieval timed out](https://www.beei.org/index.php/EEI/article/view/8884). Links: RQ1, RQ4, H1, H4B.

## P09: Real-time routing with OpenStreetMap data

Dennis Luxen; Christian Vetter, Real-time routing with OpenStreetMap data, ACM SIGSPATIAL GIS 2011, 513-516, 2011.

Access: `metadata_only`. Publication status: `conference_publication_verified`.

KIT and DBLP verify the authors, venue, pages, and DOI. The record provides routing provenance, but no detailed algorithm or runtime claim is carried forward without the primary text. It is excluded from the deep-analysis count. Current OSRM profile behavior must be documented from the actual deployed configuration separately from this historical citation.

Evidence: [KIT and DBLP bibliographic records](https://publikationen.bibliothek.kit.edu/1000028131). Links: RQ2, RQ5, H2, H5.

## P10: GeoMF++: Scalable Location Recommendation via Joint Geographical Modeling and Matrix Factorization

Defu Lian; Kai Zheng; Yong Ge; Longbing Cao; Enhong Chen; Xing Xie, GeoMF++: Scalable Location Recommendation via Joint Geographical Modeling and Matrix Factorization, ACM Transactions on Information Systems 36(3), 33, 2018.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

GeoMF++ jointly learns mobility-related geographical areas and implicit-feedback factors, evaluated on two check-in datasets with warm and cold scenarios. Its detailed parameter comparisons show that performance depends on sparsity and latent dimension. This is stronger evidence than a generic claim that adding coordinates helps. Our assessment is that geographic preference and destination-specific road travel are different constructs. The accessible manuscript predates the final 2018 metadata; the earlier GeoMF conference version is not counted as another independent study.

Evidence: [Sections 3-6; Table 1; Figures 5-7; author manuscript](https://datasciences.org/publication/GeoMF.pdf). Links: RQ2, RQ5, H2, H5.

## P11: Decision making with the analytic hierarchy process

Thomas L. Saaty, Decision making with the analytic hierarchy process, International Journal of Services Sciences 1(1), 83-98, 2008.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

AHP decomposes a decision into a hierarchy and derives priorities from pairwise judgments, with inconsistency checks. Worked examples illustrate the computation rather than a rental-relevance experiment. The explicit elicitation structure is a useful strength; our assessment is that internally consistent judgments need not match observed housing decisions. DhakaNest's normalized 1-5 inputs are a different elicitation scheme. An AHP comparison would require a prospectively approved protocol and matched preference burden, not a silent replacement of production WSM.

Evidence: [Section 3; hierarchy and consistency examples](https://untdfproyectos.wordpress.com/wp-content/uploads/2018/06/thomas-l-saaty-2008-decision-making-with-the-analytic-hierarchy-process.pdf). Links: RQ4, H4B.

## P12: A survey on multi-objective recommender systems

Dietmar Jannach; Himan Abdollahpouri, A survey on multi-objective recommender systems, Frontiers in Big Data 6, 1157899, 2023.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

The survey distinguishes competing quality, stakeholder, temporal, interface, and engineering objectives. This prevents conflating a multi-attribute rental utility with every form of multi-objective recommendation. Its strength is connecting accuracy to practical value; it supplies no universal optimal weighting. Our assessment is that DhakaNest should report constraint satisfaction and result coverage alongside relevance, and cognitive effort alongside explanations. Those tradeoffs require measured outcomes rather than assuming that more criteria or more explanation always helps.

Evidence: [Sections 1-5; tradeoffs and objective categories](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2023.1157899/full). Links: RQ3, RQ4, RQ5, H3, H4B, H5.

## P13: Hybrid Recommender Systems: A Systematic Literature Review

Erion Cano; Maurizio Morisio, Hybrid Recommender Systems: A Systematic Literature Review, Intelligent Data Analysis 21(6), 1487-1524, 2017.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

The authors screen and classify hybrid methods by problems, algorithms, combination strategy, and evaluation. Their corpus shows that combining recommenders is an established design family. A strength is transparent selection and quality assessment; the authors themselves identify weak user-oriented evidence. Our assessment is that the review supports testing separate retrieval and ranking stages, not asserting that their combination must improve relevance. The 2019 arXiv deposit and 2017 journal article represent one study and one registry entry.

Evidence: [Sections 2-5; Table 4](https://arxiv.org/pdf/1901.03888). Links: RQ1, RQ4, H1, H4A, H4B.

## P14: XGBoost: A Scalable Tree Boosting System

Tianqi Chen; Carlos Guestrin, XGBoost: A Scalable Tree Boosting System, ACM KDD 2016, 2016.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

XGBoost minimizes prediction loss plus penalties for leaf count and leaf weights, using second-order tree updates, sparse split handling, and efficient data layouts. Benchmark quality and systems results support its practicality. They do not establish rental-market calibration or superiority over every learner. Our assessment is that DhakaNest must report its own preprocessing, depth, shrinkage, sampling, regularization, and validation selection. The original objective explains model complexity, while held-out residuals establish application reliability.

Evidence: [Sections 2-5; objective Eq. 2](https://arxiv.org/pdf/1603.02754). Links: RQ6, H6.

## P15: Greedy Function Approximation: A Gradient Boosting Machine

Jerome H. Friedman, Greedy Function Approximation: A Gradient Boosting Machine, The Annals of Statistics 29(5), 1189-1232, 2001.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

The paper builds an additive predictor by descending in function space and derives regression/classification variants for different losses. It analyzes shrinkage and iteration count, explaining why model complexity cannot be summarized by tree count alone. Simulations and examples support the framework. Our assessment is that squared, absolute, and robust losses imply different responses to extreme rents; a log-transformed target does not eliminate that choice. DhakaNest should connect its fixed training configuration to this theory without treating theoretical flexibility as empirical market validation.

Evidence: [Sections 2-7; 1999 author manuscript of published work](https://www.cse.iitb.ac.in/~soumen/readings/papers/Friedman1999GreedyFuncApprox.pdf). Links: RQ6, H6.

## P16: Random Forests

Leo Breiman, Random Forests, Machine Learning 45, 5-32, 2001.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

Random forests average randomized trees and relate generalization to individual-tree strength and correlation. Out-of-bag estimates and importance measures support practical diagnostics. Classification and regression tables provide comparative evidence under specific datasets. Our assessment is that this justifies a serious bagging comparator, not an assumption that a forest is inferior to boosting. Out-of-bag accuracy also cannot substitute for a geographically distinct rental test. DhakaNest's RF validation result should be reported with the same split and comparable tuning effort.

Evidence: [Sections 3-4, 10-12](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf). Links: RQ6, H6.

## P17: CatBoost: unbiased boosting with categorical features

Liudmila Prokhorenkova; Gleb Gusev; Aleksandr Vorobev; Anna Veronika Dorogush; Andrey Gulin, CatBoost: unbiased boosting with categorical features, NeurIPS 2018, 2018.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

CatBoost addresses a specific statistical problem: using targets in category encoding and boosting can shift training predictions relative to test predictions. Ordered statistics and boosting mitigate that leakage. Benchmark and ablation evidence make this a principled alternative for high-cardinality location fields. Our assessment is that the reported classification comparisons cannot settle which model wins Dhaka rental regression. DhakaNest's selected XGBoost must therefore be described as the observed validation winner under its own preprocessing and tuning budget.

Evidence: [Sections 3-6; Table 2](https://arxiv.org/pdf/1706.09516). Links: RQ6, H6.

## P18: A Unified Approach to Interpreting Model Predictions

Scott M. Lundberg; Su-In Lee, A Unified Approach to Interpreting Model Predictions, NeurIPS 2017, 2017.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

SHAP expresses explanations as additive feature contributions and derives a unique solution under specified properties. The theory and comparative examples support a principled alternative to unqualified importance rankings. Our assessment is that contributions explain a model relative to a chosen background representation; they neither establish causal rent effects nor certify the prediction. DhakaNest must preserve preprocessing and feature alignment when explaining the saved bundle, then evaluate recommendation explanations separately from prediction attributions.

Evidence: [Sections 2-5; Theorems 1-2](https://arxiv.org/pdf/1705.07874). Links: RQ3, RQ6, H3, H6.

## P19: Why do tree-based models still outperform deep learning on typical tabular data?

Leo Grinsztajn; Edouard Oyallon; Gael Varoquaux, Why do tree-based models still outperform deep learning on typical tabular data?, NeurIPS 2022 Datasets and Benchmarks, 2022.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

The study compares tree and neural models with substantial hyperparameter search and investigates smoothness, irrelevant features, and rotation. Its 45-dataset design supports tree ensembles for the tested medium-sized tabular regime. A strength is examining mechanisms and tuning rather than a single leaderboard. Our assessment is that this is a conditional empirical finding, not universal XGBoost superiority. It supports DhakaNest's candidate selection while leaving local validation, location support, and temporal drift to project-specific evidence.

Evidence: [Sections 3-5; feature/noise/rotation experiments](https://proceedings.neurips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf). Links: RQ6, H6.

## P20: Transparency in House Rent of Dhaka: Explainable AI Based Predictive Framework

Taeef Najib; Fahim Muntasir; Wasif Al Wazed Wasi, Transparency in House Rent of Dhaka: Explainable AI Based Predictive Framework, 6th IEOM Bangladesh Conference, 2023.

Access: `full_text_examined`. Publication status: `proceedings_verified_review_process_unverified`.

The authors compare regressors, choose a tree-model voting ensemble, and use SHAP to interpret Dhaka rents. They report four predictive metrics. Local context and competing models are useful, but different splits prevent a valid numeric ranking against DhakaNest. Our assessment flags the text's claim that Random Forest needs MinMax scaling: that rationale requires scrutiny and should not be copied as a general fact. Published prediction accuracy also does not demonstrate rental recommendation relevance. Proceedings identity is verified; the review process was not independently verified.

Evidence: [Sections 3-5, especially Section 4 Data Collection; abstract results](https://ieomsociety.org/proceedings/2023dhaka/146.pdf). Links: RQ4, RQ6, H4C, H6.

## P21: Cumulated Gain-based Evaluation of IR Techniques

Kalervo Jarvelin; Jaana Kekalainen, Cumulated Gain-based Evaluation of IR Techniques, ACM Transactions on Information Systems 20(4), 422-446, 2002.

Access: `metadata_only`. Publication status: `journal_publication_verified`.

The institutional record verifies the article identity and peer-reviewed publication. Full-text retrieval failed, so the review does not attribute the exact exponential-gain variant to this paper. DhakaNest's explicit gain and discount conventions are preserved as protocol choices. This foundational citation does not count toward the full-text target.

Evidence: [Tampere record; secondary-host full-text retrieval failed](https://researchportal.tuni.fi/en/publications/cumulated-gain-based-evaluation-of-ir-techniques/). Links: RQ1, H1.

## P22: Evaluating Collaborative Filtering Recommender Systems

Jonathan L. Herlocker; Joseph A. Konstan; Loren G. Terveen; John T. Riedl, Evaluating Collaborative Filtering Recommender Systems, ACM Transactions on Information Systems 22(1), 5-53, 2004.

Access: `abstract_and_metadata_examined`. Publication status: `journal_publication_verified`.

The accessible first page and abstract connect evaluation to user tasks, datasets, accuracy measures, and whole-system user studies. They support treating prediction accuracy and user outcomes as separate constructs. Direct PDF requests timed out, so empirical details and reported metric correlations were not critically assessed. This record remains useful background but is excluded from the deep-analysis count.

Evidence: [Indexed paper first page and abstract; direct PDF timed out](https://cs.brynmawr.edu/Courses/cs380/fall2006/Herlocker2004.pdf). Links: RQ1, RQ3, H1, H3.

## P23: Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches

Maurizio Ferrari Dacrema; Paolo Cremonesi; Dietmar Jannach, Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches, ACM RecSys 2019, 2019.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

The authors reproduce available neural recommenders and tune simpler alternatives under comparable evaluation. The resulting reversals show that a complex method's reported gain can depend on weak controls and metric choices. Reproducible code and explicit tuning are strengths. Our assessment is that the findings do not establish universal neural inferiority or prove DhakaNest's simple hybrid wins. They justify equal tuning effort, clear metric conventions, and reporting all prespecified comparisons, including unfavorable outcomes.

Evidence: [Sections 2-4; baseline tuning and reproduction](https://arxiv.org/pdf/1907.06902). Links: RQ1, RQ4, H1, H4A, H4B.

## P24: Evaluation Metrics for Item Recommendation under Sampling

Steffen Rendle, Evaluation Metrics for Item Recommendation under Sampling, arXiv:1912.02263, 2019.

Access: `full_text_examined`. Publication status: `unverified_preprint`.

The paper derives how ranking a relevant item against sampled distractors changes expected evaluation metrics and can reverse relative algorithm conclusions. The analytical argument is stronger than a single observed leaderboard reversal. Our assessment is that human annotation pooling is related but not identical: sampling unobserved alternatives still changes the scope of the estimand. DhakaNest should identify the judged pool explicitly and avoid presenting pooled NDCG as full-market performance. The related later publication is not counted as another version of this study.

Evidence: [Sections 2-5; exact versus sampled metric derivation](https://arxiv.org/pdf/1912.02263). Links: RQ1, RQ5, H1, H5.

## P25: Candidate Set Sampling for Evaluating Top-N Recommendation

Ngozi Ihemelandu; Michael D. Ekstrand, Candidate Set Sampling for Evaluating Top-N Recommendation, IEEE/WIC WI-IAT 2023, 2023.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

The study varies candidate-selection distributions and uses simulation to examine popularity-related bias relative to more complete evidence. It shows why choosing distractors is part of the evaluation method rather than a harmless speed optimization. Its strength is testing interactions between observed data and sampling. Our assessment is that rental annotation pools need source accounting and sensitivity checks because their bias cannot be inferred directly from movie or music datasets. This supports recording method-pooled, random, and hard-negative contributions separately.

Evidence: [Sections II-IV; candidate sampling and simulation](https://arxiv.org/pdf/2309.11723). Links: RQ1, RQ5, H1, H5.

## P26: Explaining the user experience of recommender systems

Bart P. Knijnenburg; Martijn C. Willemsen; Zeno Gantner; Hakan Soncu; Chris Newell, Explaining the user experience of recommender systems, User Modeling and User-Adapted Interaction 22, 441-504, 2012.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

The framework links objective system aspects to perceptions, experienced process/outcome quality, and behavior while accounting for personal and situational differences. Several field and controlled studies test these links with structural equation models. That breadth is a strength. Our assessment is that modeled mediation alone cannot establish every causal relationship. DhakaNest should measure decision relevance and time separately from trust and satisfaction, control task ordering, and avoid treating favorable ratings as evidence of objectively better housing choices.

Evidence: [Framework and validation studies; SEM appendix](https://link.springer.com/content/pdf/10.1007/s11257-011-9118-4.pdf). Links: RQ3, H3.

## P27: Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure

David R. Roberts; Volker Bahn; Simone Ciuti; Mark S. Boyce; Jane Elith; Gurutzeta Guillera-Arroita; Severin Hauenstein; Jose J. Lahoz-Monfort; Boris Schroder; Wilfried Thuiller; David I. Warton; Brendan A. Wintle; Florian Hartig; Carsten F. Dormann, Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure, Ecography 40(8), 913-929, 2017.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

Simulations and case studies compare random and blocked validation for dependent observations. Blocking can reduce overly optimistic error when predicting new space or time, but can also induce extrapolation and overstate interpolation error. That balanced argument is a strength. Our assessment is that random Dhaka property splits estimate a narrower task than transfer to unseen neighborhoods or future markets. New geographic/temporal analyses should identify the intended deployment task and preserve the official historical split rather than retroactively replacing it.

Evidence: [Simulation sections; blocking recommendations](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/ecog.02881). Links: RQ5, RQ6, H5, H6.

## P28: Accounting for Variance in Machine Learning Benchmarks

Xavier Bouthillier; Pierre Delaunay; Mirko Bronzi; Assya Trofimov; Brennan Nichyporuk; Justin Szeto; Naz Sepah; Edward Raff; Kanika Madan; Vikram Voleti; Samira Ebrahimi Kahou; Vincent Michalski; Dmitriy Serdyuk; Tal Arbel; Chris Pal; Gael Varoquaux; Pascal Vincent, Accounting for Variance in Machine Learning Benchmarks, Proceedings of Machine Learning and Systems 3, 2021.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

The paper models data sampling, initialization, and tuning as distinct variation sources and compares practical estimators of algorithm performance. Its strength is showing why a single favorable run or seed can mislead. Our assessment is that bootstrapping DhakaNest's frozen predictions measures conditional test uncertainty, not uncertainty in retraining or hyperparameter selection. These should be labeled separately. The registry follows the PDF author list and records its disagreement with the proceedings landing-page list instead of silently merging names.

Evidence: [Sections 2-5; paper author list differs from landing-page list](https://proceedings.mlsys.org/paper_files/paper/2021/file/0184b0cd3cfb185989f858a1d9f5c1eb-Paper.pdf). Links: RQ1, RQ5, RQ6, H1, H5, H6.

## P29: Conformalized Quantile Regression

Yaniv Romano; Evan Patterson; Emmanuel J. Candes, Conformalized Quantile Regression, NeurIPS 2019, 2019.

Access: `full_text_examined`. Publication status: `conference_publication_verified`.

CQR fits conditional quantiles and uses held-out conformity scores to calibrate prediction intervals. Theory and regression experiments examine coverage and length, including heteroscedastic settings. The key strength is an explicit marginal guarantee under exchangeability. Our assessment is that this does not guarantee neighborhood-specific or future-market coverage. DhakaNest currently has point predictions and should not describe residual spread as a calibrated interval. Adopting CQR later would require separate data allocation and authorization, with no official-test tuning.

Evidence: [Sections 2-4 and 6](https://arxiv.org/pdf/1905.03222). Links: RQ6, H6.

## P30: Predictive inference with the jackknife+

Rina Foygel Barber; Emmanuel J. Candes; Aaditya Ramdas; Ryan J. Tibshirani, Predictive inference with the jackknife+, The Annals of Statistics 49(1), 486-507, 2021.

Access: `full_text_examined`. Publication status: `journal_publication_verified`.

Jackknife+ combines leave-one-out residuals with predictions for the new point, addressing fitted-model variability omitted by naive jackknife intervals. Coverage theory and empirical analysis clarify stability assumptions and costs. Our assessment is that this gives DhakaNest an uncertainty research direction, not a guarantee already possessed by its fixed XGBoost bundle. The paper's marginal coverage statements should not be restated as exact conditional protection for a particular rental or neighborhood. No resampling fits are authorized in this phase.

Evidence: [Sections 2-4; coverage theorems and simulations](https://arxiv.org/pdf/1905.02928). Links: RQ6, H6.

## P31: Multi-criteria journey aware housing recommender system

Elizabeth M. Daly; Adi Botea; Akihiro Kishimoto; Radu Marinescu, Multi-criteria journey aware housing recommender system, ACM RecSys 2014, 325-328, 2014.

Access: `abstract_and_metadata_examined`. Publication status: `conference_publication_verified`.

The author-hosted abstract explicitly combines rent, transport links to user-specified locations, multihop journey calculation, and multi-criteria solution selection, and states a user study. This is enough to reject an absolute destination-first novelty claim. Full-text experimental details remain unavailable, so no dataset size, effect size, or detailed feature absence is inferred. It is a priority comparator for primary-text retrieval and a later journey-aware baseline specification, but does not count toward the deep-analysis target.

Evidence: [IBM author abstract; survey P02 Section 4.4 is secondary context only](https://research.ibm.com/publications/multi-criteria-journey-aware-housing-recommender-system). Links: RQ1, RQ2, RQ3, H1, H2, H3.
