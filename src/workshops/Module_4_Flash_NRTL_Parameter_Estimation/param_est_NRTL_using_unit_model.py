from pyomo.environ import ConcreteModel
from idaes.core import FlowsheetBlock
import idaes.logger as idaeslog
from idaes.generic_models.properties.activity_coeff_models.\
    BTX_activity_coeff_VLE import BTXParameterBlock
from idaes.generic_models.unit_models import Flash

import pyomo.contrib.parmest.parmest as parmest
import pandas as pd
# Set tag level to see output logs; here we want to see log messages
# down to the properties level
idaeslog.add_log_tag("properties")

# Create model function
def NRTL_model(data):
    m = ConcreteModel()
    m.fs = FlowsheetBlock(default={"dynamic": False})
    m.fs.properties = BTXParameterBlock(default={"valid_phase":
                                                 ('Liq', 'Vap'),
                                                 "activity_coeff_model":
                                                 'NRTL'})

    m.fs.flash = Flash(default={"property_package": m.fs.properties})

    # Initialize at a certain inlet condition
    m.fs.flash.inlet.flow_mol.fix(1)
    m.fs.flash.inlet.temperature.fix(368)
    m.fs.flash.inlet.pressure.fix(101325)
    m.fs.flash.inlet.mole_frac_comp[0, "benzene"].fix(0.5)
    m.fs.flash.inlet.mole_frac_comp[0, "toluene"].fix(0.5)

    # Set Flash unit specifications
    m.fs.flash.heat_duty.fix(0)
    m.fs.flash.deltaP.fix(0)

    # Fix NRTL specific variables
    # alpha values (set at 0.3)
    m.fs.properties.\
        alpha["benzene", "benzene"].fix(0)
    m.fs.properties.\
        alpha["benzene", "toluene"].fix(0.3)
    m.fs.properties.\
        alpha["toluene", "toluene"].fix(0)
    m.fs.properties.\
        alpha["toluene", "benzene"].fix(0.3)

    # initial tau values
    m.fs.properties.\
        tau["benzene", "benzene"].fix(0)
    m.fs.properties.\
        tau["benzene", "toluene"].fix(0.1690)
    m.fs.properties.\
        tau["toluene", "toluene"].fix(0)
    m.fs.properties.\
        tau["toluene", "benzene"].fix(-0.1559)

    # Initialize the flash unit
    m.fs.flash.initialize(outlvl=idaeslog.INFO)

    # Fix at actual temperature
    m.fs.flash.inlet.temperature.fix(float(data["temperature"]))

    # Set bounds on variables to be estimated
    m.fs.properties.\
        tau["benzene", "toluene"].setlb(-5)
    m.fs.properties.\
        tau["benzene", "toluene"].setub(5)

    m.fs.properties.\
        tau["toluene", "benzene"].setlb(-5)
    m.fs.properties.\
        tau["toluene", "benzene"].setub(5)

    # Return initialized flash model
    return m

# Parameter Estimation using parmest

# Vars to estimate
variable_name = ["fs.properties.tau['benzene', 'toluene']",
                 "fs.properties.tau['toluene', 'benzene']"]

# Using excel
data = pd.read_excel('BT_NRTL_dataset.xlsx')

# Create expression to compute the sum of squared error
def SSE(m, data):
    expr = ((float(data["vap_benzene"]) -
             m.fs.flash.vap_outlet.mole_frac_comp[0, "benzene"])**2 +
            (float(data["liq_benzene"]) -
             m.fs.flash.liq_outlet.
             mole_frac_comp[0, "benzene"])**2)
    return expr

pest = parmest.Estimator(NRTL_model, data, variable_name, SSE, tee=True)

SSE, parameters = pest.theta_est()
print(SSE)
print(parameters)


# bootstrap_theta = pest.theta_est_bootstrap(10)
# print(bootstrap_theta.head())
#
# parmest.pairwise_plot(bootstrap_theta)
# parmest.pairwise_plot(bootstrap_theta, variable_name, 0.8,
#                       ['tau["benzene", "toluene"]',
#                        'tau["toluene", "benzene"]'])
