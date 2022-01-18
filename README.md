# Ner Test suite


_Test suite for [Self-supervised NER](https://ajitrajasekharan.github.io/2021/01/02/my-first-post.html)_

# Prerequisites 

Python 3.x

# Usage 

1. This test suite has 11 benchmarks. The tests take the ner output runs from the self-supervised NER link mentioned above. These output runs are two columun format files with _term_ and _entity type_ , with the only addition that the prediction could be two predictions with subtypes for each prediction as oppposed to just one prediction (which is the normal case). 
2. The test sentences are generated from the two column test.tsv file (containing _term_ and _ground truth prediction_ ). While doing so, a specified sample of sentences are POS tagged _(if this option is chosen in the config)_ to compare phrase spans in test set with phrase spans of a POS tagger. This is to examine if the test set tagging is consistent with a POS tagger. 
3. The evaluation of an NER output can be done in two ways (1) standard single prediction output only by just taking the first prediction _(-strict)_ or (2) picking the prediction of the two, that matches ground truth. The performance numbers are reported separately. The evaluation also has an otion to skip false positive reporting on sentences with just the OTHER tag _(-ignore_others option; set to false by default)_ THis is explained in the _[Self-supervised post NER](https://ajitrajasekharan.github.io/2021/01/02/my-first-post.html)_
