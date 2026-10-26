# Thematic Synthesis

Paper IDs refer to `paper_registry.json` and the individual reviews.

## A. Housing recommendation

P01 and P03 show property recommendation using behavior-informed content
retrieval and additional ranking stages. P02 documents a wider mix of
knowledge, similarity, and decision methods. Their results answer different
questions from independently judged rental suitability. Accordingly, DhakaNest
should compare explicit-needs ranking to operational controls and report its
source/label limitations, rather than use click prediction as an interchangeable
target. [P01](https://arxiv.org/html/2404.16553v1),
[P03](https://opus.lib.uts.edu.au/bitstream/10453/148303/2/Domain_ISKE_submit.pdf).

## B. Destination and commute awareness

P04 is a direct reachability-centered housing precedent; P31's author abstract
also explicitly connects housing choices with journeys to specified places.
P10 instead learns geographical preferences from mobility histories. These are
different location constructs. Road routes, observed trajectory accessibility,
and spatial preference should not be described as equivalent.
[P04](https://dwe.ng/pdf/reach.pdf),
[P31](https://research.ibm.com/publications/multi-criteria-journey-aware-housing-recommender-system).

## C. Multiple criteria

P11's pairwise elicitation and P12's objective taxonomy demonstrate that a
weighting method needs a declared interpretation. DhakaNest's direct priority
normalization is a modeling choice; neither normalization nor five criteria
proves agreement with renters. Component removal therefore requires explicit
weight policy and independent judgments.
[P11](https://doi.org/10.1504/IJSSCI.2008.017590),
[P12](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2023.1157899/full).

## D. Rent prediction

P14-P19 support careful consideration of ensemble methods, categorical encoding,
complexity, and attribution. P20 establishes local prediction/explanation
precedent. P27, P29, and P30 show why split design and uncertainty assumptions
matter. Their different datasets and target definitions prevent cross-paper MAE
leaderboards. DhakaNest's validation winner remains a project-specific finding.
[P14](https://arxiv.org/pdf/1603.02754),
[P20](https://ieomsociety.org/proceedings/2023dhaka/146.pdf).

## E. Evaluation

P23-P25 motivate explicit candidate universes, credible simple controls, and
sampling sensitivity. P26 separates experience from behavior, while P28 warns
that conditional uncertainty in frozen outputs is narrower than variation in
the complete learning pipeline. The existing eight-profile benchmark remains
preliminary; both historical NDCG values predate demonstrated v4 evidence.
[P23](https://arxiv.org/pdf/1907.06902),
[P25](https://arxiv.org/pdf/2309.11723).

## F. Hybrid and explanation

P13 establishes that hybrids are a mature family. P06's graph counterfactuals,
P18's prediction attributions, and DhakaNest's criterion reasons answer different
explanation questions. User trust, fidelity to scoring, and decision usefulness
need separate evidence. A readable explanation is not proof of correct rent or
correct ranking. [P13](https://arxiv.org/pdf/1901.03888),
[P06](https://arxiv.org/pdf/2602.05861),
[P18](https://arxiv.org/pdf/1705.07874).
