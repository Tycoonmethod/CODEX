import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib.pyplot as plt
import seaborn as sns

np.random.seed(42)
n = 200
n_iter = 1000

r2_scores = []
bp_pvalues = []
vif_maxs = []
n_significant = []
resid_means = []
resid_stds = []

for _ in range(n_iter):
    data = {
        "UAT": np.random.uniform(60, 100, n),
        "Migration": np.random.uniform(50, 100, n),
        "E2E": np.random.uniform(60, 100, n),
        "Training": np.random.uniform(30, 100, n),
        "Resources": np.random.uniform(70, 100, n),
        "Hypercare": np.random.uniform(50, 100, n),
    }
    df = pd.DataFrame(data)
    df["Quality"] = (
        1.20
        + 0.30 * df["UAT"]
        + 0.20 * df["Migration"]
        + 0.15 * df["E2E"]
        + 0.10 * df["Training"]
        + 0.10 * df["Resources"]
        + 0.12 * df["Hypercare"]
        + np.random.normal(0, 2, n)
    )
    X = df[["UAT", "Migration", "E2E", "Training", "Resources", "Hypercare"]]
    X = sm.add_constant(X)
    y = df["Quality"]
    model = sm.OLS(y, X).fit()
    r2_scores.append(model.rsquared)
    # Breusch-Pagan
    bp_test = het_breuschpagan(model.resid, model.model.exog)
    bp_pvalues.append(bp_test[1])
    # VIF
    vif = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
    vif_maxs.append(np.max(vif))
    # Coeficientes significativos
    n_significant.append(np.sum(model.pvalues < 0.05))
    # Residuos
    resid_means.append(np.mean(model.resid))
    resid_stds.append(np.std(model.resid))

# Gráficas
fig, axs = plt.subplots(2, 3, figsize=(18, 10))
sns.histplot(r2_scores, bins=30, kde=True, ax=axs[0, 0])
axs[0, 0].set_title("Distribución de R²")
axs[0, 0].axvline(
    np.mean(r2_scores),
    color="red",
    linestyle="--",
    label=f"Media={np.mean(r2_scores):.3f}",
)
axs[0, 0].legend()

sns.histplot(bp_pvalues, bins=30, kde=True, ax=axs[0, 1])
axs[0, 1].set_title("p-valor Breusch-Pagan")
axs[0, 1].axvline(0.05, color="red", linestyle="--", label="0.05")
axs[0, 1].legend()

sns.histplot(vif_maxs, bins=30, kde=True, ax=axs[0, 2])
axs[0, 2].set_title("VIF máximo")
axs[0, 2].axvline(5, color="red", linestyle="--", label="VIF=5")
axs[0, 2].legend()

sns.histplot(n_significant, bins=range(6, 9), kde=False, ax=axs[1, 0])
axs[1, 0].set_title("Coeficientes significativos (<0.05)")
axs[1, 0].set_xticks(range(6, 9))

sns.histplot(resid_means, bins=30, kde=True, ax=axs[1, 1])
axs[1, 1].set_title("Media de residuos")

sns.histplot(resid_stds, bins=30, kde=True, ax=axs[1, 2])
axs[1, 2].set_title("Desviación estándar de residuos")

plt.tight_layout()
plt.show()

# Resumen estadístico
print(f"Media R²: {np.mean(r2_scores):.3f} | Desv. Std: {np.std(r2_scores):.3f}")
print(
    f"Porcentaje de iteraciones sin heterocedasticidad (p>0.05): {np.mean(np.array(bp_pvalues)>0.05)*100:.1f}%"
)
print(
    f"VIF máximo promedio: {np.mean(vif_maxs):.2f} | Máximo observado: {np.max(vif_maxs):.2f}"
)
print(
    f"Coeficientes significativos promedio: {np.mean(n_significant):.2f} de 7 posibles"
)
print(f"Media de residuos promedio: {np.mean(resid_means):.4f}")
print(f"Desviación estándar de residuos promedio: {np.mean(resid_stds):.3f}")
