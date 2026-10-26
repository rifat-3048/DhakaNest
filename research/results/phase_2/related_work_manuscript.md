# Related Work

Numeric citations map directly to registry IDs: [1] = P01, ... [31] = P31.
Complete bibliographic entries are in `references.bib` and the evidence matrix.

## Real-estate and rental recommendation

Property recommendation has distinctive cold-start, sparse-interaction, and
preference-elicitation demands. A domain survey organizes approaches across
content, collaborative, knowledge-based, multi-criteria, and hybrid families
([2](https://www.mdpi.com/2076-3417/11/16/7502)). RE-RecSys illustrates a
history-sensitive production pipeline, while a cold-item property study uses
content retrieval followed by learned filtering
([1](https://arxiv.org/html/2404.16553v1),
[3](https://opus.lib.uts.edu.au/bitstream/10453/148303/2/Domain_ISKE_submit.pdf)).
Such engagement-oriented systems motivate staged comparisons but do not by
themselves establish suitability for an explicitly stated tenant request.

## Location and journeys

Housing choice around journeys is established prior work. HomeFinder Revisited
offers reachability-centered visual decision support, and Daly and colleagues'
author abstract explicitly describes housing costs and transport to specified
locations ([4](https://dwe.ng/pdf/reach.pdf),
[31](https://research.ibm.com/publications/multi-criteria-journey-aware-housing-recommender-system)).
Geographical factorization learns a different signal from mobility histories
([10](https://doi.org/10.1145/3182166)). These distinctions motivate separating
spatial preference, static route estimates, and observed journey accessibility.
DhakaNest's formulation should therefore be evaluated as a particular
integration rather than presented as the invention of destination-aware housing.

## Hybrid retrieval and multiple criteria

Hybrid recommenders are a mature family, and their benefit depends on the task
and evaluation ([13](https://doi.org/10.3233/IDA-163209)). Weight elicitation
and competing objectives also require explicit semantics
([11](https://doi.org/10.1504/IJSSCI.2008.017590),
[12](https://doi.org/10.3389/fdata.2023.1157899)). DhakaNest separates content
candidate selection from tenant-priority utility ranking. KNN-only, WSM-only,
and controlled criterion ablations are necessary to establish each stage's
contribution.

## Rental prediction and explanation

Boosting, random forests, and categorical boosting provide distinct ensemble
strategies ([14](https://arxiv.org/pdf/1603.02754),
[15](https://doi.org/10.1214/aos/1013203451),
[16](https://doi.org/10.1023/A:1010933404324),
[17](https://arxiv.org/pdf/1706.09516)). Tabular benchmarks support careful
tree-based comparisons within their tested regimes
([19](https://proceedings.neurips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf)).
Dhaka rent prediction with model explanation already has local precedent
([20](https://ieomsociety.org/proceedings/2023dhaka/146.pdf)). Prediction
attributions ([18](https://arxiv.org/pdf/1705.07874)) and property graph
counterfactuals ([6](https://arxiv.org/pdf/2602.05861), preprint) address
different explanation goals. Stored predicted-rent reasonableness must be
evaluated for recommendation value separately from regression error.

## Evaluation and remaining evidence

Credible simple controls and candidate-set conventions can change conclusions
([23](https://arxiv.org/pdf/1907.06902),
[24](https://arxiv.org/pdf/1912.02263), preprint,
[25](https://arxiv.org/pdf/2309.11723)). Housing-interface experiments and
user-experience research motivate measuring decisions and perceptions
separately ([5](https://doi.org/10.1145/133160.133216),
[26](https://doi.org/10.1007/s11257-011-9118-4)). Structured validation and
benchmark variance further constrain generalization claims
([27](https://doi.org/10.1111/ecog.02881),
[28](https://arxiv.org/pdf/2103.03098)). The remaining task is to test
DhakaNest's specific framework with frozen inputs, independent labels, strong
journey-aware comparisons, uncertainty estimates, and controlled user tasks.
No superiority result is asserted here.
