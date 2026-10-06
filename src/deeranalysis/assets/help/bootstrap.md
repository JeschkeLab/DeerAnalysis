
DeerLab offers two approaches to uncertainty estimation: moment based and bootstrapped. The moment based approach (the default) is fast, but may not be accurate for complex models. Bootstrapped uncertainty estimation is more accurate, but comes at the cost of increased computation time.

## Moment Based Uncertainty Estimation

The uncertainty is calculated from the covariance matrix of the fitted parameters, which is derived from the Jacobian of the model. 
This method assumes that all uncertanty distributions are normal (Gaussian) in nature, which may not be the case for complex models. 
It is particulaly useful for simple models or for an initial estimate of the uncertainty, as it is fast and does not require additional computation time.

## Bootstrap Uncertainty Estimation

Bootsrapped uncertainty estimation is a method of computing uncertainties by resampling the data with different noise models. This is achieved by first fitting the model to the data, and then calculating the noise. Random synthetic noise is then added to the data, and the model is refitted. This process is repeated many times, and the distribution of the fitted parameters is used to estimate the uncertainty.
It is particulaly useful for complex models, where the uncertainty estimation is not straightforward, such as dipolar EPR. However, it comes at the cost of significant increases in computation time, which can be partially offset by using parallel processing. 

For publication quality figures it is recommended to use the bootstrapped method for uncertainty estimation, with at least 250 bootstrap samples. 

## Common Pitfalls

- A distance distribution can have a tight uncerctainty, but still be a poor fit to the data. Always check the fit quality and residuals, and do not rely solely on the distance domain uncertainty estimation.