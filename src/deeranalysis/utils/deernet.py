
from typing import Tuple
import numpy as np
from numpy.random import rand
from scipy.interpolate import pchip_interpolate
from scipy.optimize import minimize,least_squares
from dataclasses import dataclass
import scipy.constants as const
import h5py as h5
import onnxruntime as rt

@dataclass
class DEERnetResult:
    """ This is a dataclass developed for the holding of deernet data.\n
    By:\n
    hkaras@ethz.ch
    """
    raw_data:       np.ndarray
    raw_time:       np.ndarray
    dn_input:  np.ndarray
    dn_time_axis: np.ndarray
    n_traces:       int


def deernet_prep(input_axis:np.ndarray, input_traces:np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """deernet_prep [This functions prepares an input dataset for running through deernet. It does this by
     rephasing the input to be only real and cutting all data before the maximal point. This does not resample
     the data to be 512 data points. \n
     This was coppied from MATLAB code by:\n
     gunnar.jeschke@phys.chem.ethz.ch\n
     s.g.worswick@soton.ac.uk\n
     i.kuprov@soton.ac.uk\n
    ]

    :param input_axis: [An array of the time axis of the input data in microseconds]
    :type input_axis: np.ndarray
    :param input_traces: [A real or complex valued array containg the time domain deer trace]
    :type input_traces: np.ndarray
    :return: [A tuple containing two real valued arrays. The first is the post processed time axis and the second is the 
    processed time domain deer data]
    :rtype: Tuple[np.ndarray, np.ndarray]
    """

    if input_traces.dtype == np.complex128:
        real_part = np.real(input_traces)
        imag_part = np.imag(input_traces)

        scaling = np.linalg.norm(real_part+ 1j*imag_part)

        opt_fun = lambda phi: np.linalg.norm((np.sin(phi)*real_part/scaling) + (np.cos(phi)*imag_part/scaling)) **2

        result = least_squares(opt_fun,0)
        phi = result.x

        new_real = np.cos(phi) * real_part - np.sin(phi) * imag_part
        new_imag = np.sin(phi) * real_part + np.cos(phi) * imag_part

        print(f'WARNING: Complex data auto phased. phi={180*phi/np.pi} degrees')

        if np.sum(new_real) >0:
            input_traces = new_real
        else:
            input_traces = new_real * -1
    
    max_pos = np.argmax(input_traces)

    if max_pos >0:
        print(f'WARNING: time axis shifted')
        input_traces = input_traces[max_pos:]
        input_axis = input_axis[max_pos:]
        input_axis = input_axis - input_axis[0]

    input_axis = input_axis * 1e-6
    input_axis = np.double(input_axis)
    input_traces = np.double(input_traces)
    
    return [input_axis,input_traces]



def quality_control(dataset:DEERnetResult) -> DEERnetResult:
    """quality_control [heuristic tests designed to prevent
    unskilled users from shooting themselves in the foot]

    :param dataset: [The output dataclass from the running Pydeernet]
    :type dataset: DEERnetResult
    :return: [The same dataclass as the input with NaN replacing any/all unreliable values]
    :rtype: DEERnetResult
    """
    for n in range(0,dataset.n_traces):
        all_nets_posivite_md = all(dataset.mdpths[0,n,:]>0)
        average_md_decent = np.mean(dataset.mdpths[0,n,:]) > 0.005

        if (not all_nets_posivite_md) or (not average_md_decent):
            dataset.dist_av[:,n] = np.nan
            dataset.dist_lb[:,n] = np.nan
            dataset.dist_ub[:,n] = np.nan

        long_edge_peak = dataset.dist_ub[-1,:] > 0.20 * dataset.dist_av[:,n].max()

        if long_edge_peak:
            print('WARNING: significant distance density at the long edge;\n' \
                  '         you are pushing your luck, consider recording\n '\
                  '         a longer DEER trace or cutting stray echoes.\n')

        #Do we have an unstable background estimate?
        bg_head_wobble = (dataset.backgs_ub[0,n] - dataset.backgs_lb[0,n]) / dataset.backgs_av[0,n]
        bg_tail_wobble = (dataset.backgs_ub[-1,n] - dataset.backgs_lb[-1,n]) / dataset.backgs_av[-1,n]
        wobbly_background = (bg_head_wobble > 0.40 * dataset.mdpths_av[0,n]) or \
                            (bg_tail_wobble > 0.20 * dataset.mdpths_av[0,n])
        if wobbly_background:
            print('WARNING: networks disagree on the background signal;\n'\
                  '         modulation depth cannot be estimated.\n')
        
        if long_edge_peak or wobbly_background or (not all_nets_posivite_md) or (not average_md_decent):
            dataset.backgs_av[:,n] = np.nan
            dataset.backgs_lb[:,n] = np.nan
            dataset.backgs_ub[:,n] = np.nan
            dataset.mdpths_av[:,n] = np.nan
            dataset.mdpths_std[:,n] = np.nan
    
    return dataset
        

def deernet(dataset, providor=None) -> DEERnetResult:
    """deernet [Use pre-trained neural networks to extract background signals and 
                distance distributions from DEER data. See our papers:\n

                https://dx.doi.org/10.1126/sciadv.aat5218\n
                https://arxiv.org/abs/1912.01498]\n

                This code has been converted and modified from impressive work by:\n
                jake.keeley@soton.ac.uk\n
                tajwar.choudhury@soton.ac.uk\n
                s.g.worswick@soton.ac.uk\n
                gunnar.jeschke@phys.chem.ethz.ch\n
                i.kuprov@soton.ac.uk\n

    :param time_axis: [description]
    :type time_axis: np.ndarray
    :param data_axis: [description]
    :type data_axis: np.ndarray
    :return: [description]
    :rtype: DEERnetResult
    """

    if 't' in dataset.coords:

        time_axis = dataset.t.values
    else:
        time_axis = dataset.coords[list(dataset.coords)[0]].values
    data_axis = dataset.values

    time_axis, data_axis = deernet_prep(time_axis, data_axis)
    # resample the input data to match input dimension
    n_points = 512
    new_axis = np.linspace(min(time_axis),max(time_axis),n_points) 
    resamp_traces = pchip_interpolate(time_axis,data_axis,new_axis)

    # Renormalize input trace to 0:1
    new_trace = resamp_traces
    scaling_factors = np.max(resamp_traces)
    new_trace = new_trace - min(new_trace)
    new_trace = new_trace / max(new_trace)

    # Create distance axis

    gamma = const.value(u'electron gyromag. ratio')
    dt = new_axis[1]-new_axis[0]
    def calc_rmin(dt):
        return 1e10 * (4 * (const.mu_0 / (4 * np.pi)) * (gamma **2 *const.hbar / (2 * np.pi)) * dt) **(1/3)
    def calc_rmax(tmax):
        return 1e10 * (2* (const.mu_0 / (4*np.pi)) * (gamma **2 * const.hbar/(2*np.pi))*tmax)**(1/3)
    new_rmin = calc_rmin(new_axis[1]-new_axis[0])
    new_rmax = calc_rmax(new_axis.max())
    input_rmin = calc_rmin(time_axis[1]-time_axis[0])
    input_rmax = calc_rmax(np.max(time_axis))
    new_dist = np.linspace(new_rmin,new_rmax,n_points)

    dist_keep_mask = (new_dist>input_rmin) & (new_dist<input_rmax)

    n_traces = 1
    n_nets = 32 
    backgs = np.zeros((n_points,n_traces,n_nets),dtype=float)
    distds = np.zeros((n_points,n_traces,n_nets),dtype=float)
    retros = np.zeros((n_points,n_traces,n_nets),dtype=float)
    mdpths= np.zeros((1,n_traces,n_nets),dtype=float)

    # loop over networks

    for n in range(0,n_nets):
        nets_path = "/Users/hugo/Documents/Work/GitHub/DeerAnalysis/deernet/nets/net_distan_dd/512_512/"
        # nets_path = MODULE_DIR[0] + "/nets/net_distan_dd/512_512/"
        net_file = nets_path + f"{n+1}_cor.onnx"
        param_file_path = nets_path + f"{n+1}.h5"
        
        #Run neural network
        providers = ['CPUExecutionProvider']
        m = rt.InferenceSession(net_file,providers=providers)
        # print(f'Using provider: {m.get_providers()}')
        input_trace = new_trace.astype(np.float32)
        input_trace = input_trace.reshape([1,512])
        deer_trace = m.run(['Renorm'],{"input":input_trace})
        deer_trace = np.transpose(np.squeeze(deer_trace))
        deer_trace = deer_trace * len(deer_trace)

        if np.isnan(deer_trace).any() == True:
            raise RuntimeError('Neural net returns NaN, check your input data.')
        
        # Extract the kernel
        param_file = h5.File(param_file_path,mode='r')
        kernel = param_file['kernel'][()]
        kernel[:,0] = 0
        ffs = np.matmul(np.transpose(kernel), (deer_trace / np.sum(deer_trace)))
        ffs[0,] = 1
        ffs = np.double(ffs)
        
        def finite_vals(array:np.ndarray) -> np.ndarray:
            return array[np.logical_not(np.isnan(array))]

        def signal_mode(x,ffs,ntraces):
            alphas = np.transpose(x[0:ntraces])
            mus = np.transpose(x[ntraces:2*ntraces])
            k = x[2*ntraces]
            bgd=x[2*ntraces+1]

            scaled_time = np.linspace(0,1,np.size(ffs))
            
            sig = alphas * ((1 - mus) + mus *ffs) * np.exp(- (k * scaled_time) **(bgd / 3))
            return sig

        scaled_traces = resamp_traces / scaling_factors
        lsq_err = lambda x: sum( finite_vals( scaled_traces - signal_mode(x,ffs,n_traces) )**2)

        # Create initial conditions
        amp_scale =     0.50 * (1.0 + rand()) * np.ones(n_traces)
        mod_depths =    0.50 * (1.0 + rand()) * np.ones(n_traces)
        bgd_rate =      0.50 * (1.0 + rand())
        bgd_dim =       2.0  +  1.5 * rand()

        guess = np.hstack((amp_scale,mod_depths,bgd_rate,bgd_dim)) # place in a single 1D array

        bounds = [  (np.full([n_traces,1],-np.inf) , np.full([n_traces,1],+np.inf)    ),\
                    (np.full([n_traces,1],-np.inf) , np.full([n_traces,1],+np.inf)    ),\
                    (0                             , +np.inf                          ),\
                    (2.0                           , 3.5                              )]

        # This is one of the big difference between the MATLAB and Python versions. In the Python version 
        # a different method is used to minimise this function.
        result = minimize(lsq_err,guess,args=(),method = 'L-BFGS-B',bounds = bounds) 
        x = result.x

        retros[:,:,n] = scaling_factors * signal_mode(x,    ffs,    n_traces).reshape([n_points,n_traces])
        backgs[:,:,n] = scaling_factors * signal_mode(x,    0*ffs,  n_traces).reshape([n_points,n_traces])

        mdpths[0,:,n] = x[n_traces:(2*n_traces)]
        distds[:,:,n] = mdpths[0,:,n] * deer_trace.reshape([n_points,n_traces])

    ## Generating Data
    dataset = DEERnetResult(
        data_axis,
        time_axis,
        input_trace,
        new_axis,
        n_traces,
    )

    dataset.backgs_av = np.mean(backgs,2)
    dataset.backgs_lb = np.mean(backgs,2) - 2 * np.std(backgs,2)
    dataset.backgs_ub = np.mean(backgs,2) + 2 * np.std(backgs,2)

    dataset.retros_av = np.mean(retros,2)
    dataset.retros_lb = np.mean(retros,2) - 2 * np.std(retros,2)
    dataset.retros_ub = np.mean(retros,2) + 2 * np.std(retros,2)

    dataset.mdpths = mdpths
    dataset.mdpths_av = np.mean(mdpths,2)
    dataset.mdpths_std = np.mean(mdpths,2)

    dist_av = np.mean(distds,2)
    dist_lb = np.mean(distds,2) - 2 * np.std(distds,2)
    dist_ub = np.mean(distds,2) + 2 * np.std(distds,2)
    dist_lb[dist_lb<0] = 0

    #Apply distance range truncation
    dataset.dist_av = dist_av[dist_keep_mask]
    dataset.dist_lb = dist_lb[dist_keep_mask]
    dataset.dist_ub = dist_ub[dist_keep_mask]
    dataset.dist_ax = new_dist[dist_keep_mask]

    dataset.resamp_traces = resamp_traces

    dataset = quality_control(dataset)

    return dataset