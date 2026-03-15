# Quantpy

Project structure:
instruments/ — what is the contract. Exposes payoff(spot) or cashflows(path)
curves/ — what is the market. Vol surfaces, discount curves, forward curves
models/ — what is the distribution. Simulates or solves for the expected payoff under the pricing measure, undiscounted
price_and_risk/ — what is it worth. Applies discount factors, aggregates, computes Greeks
