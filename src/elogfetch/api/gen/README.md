# Generated models from claude sonnet 4.6

We used `scripts/experiment_dump.py` to output jsons for each of the endpoints in elog.

Then we used these outputs to generate pydantic models. These may not be correct, but serve as a good starting point for future work on API contracts.

[models.py](models.py) are the models, and [endpoint_models.py](endpoint_models.py) is the mapping from endpoint -> model.
