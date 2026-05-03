# Quantpy

Project structure: <br>
instruments/ — what is the contract. Exposes payoff(spot) or cashflows(path) <br>
curves/ — what is the market. Vol surfaces, discount curves, forward curves <br>
models/ — what is the distribution. Simulates or solves for the expected payoff under the pricing measure, undiscounted <br>
price_and_risk/ — what is it worth. Applies discount factors, aggregates, computes Greeks <br>
time/ - holds all time logic <br>
