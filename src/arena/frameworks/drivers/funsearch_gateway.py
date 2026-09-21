"""Prepared native FunSearch pilots with exact gateway IDs and namespace scoring."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import time
import uuid

from ._namespace_sandbox import NamespaceSandbox
from .base_gateway import MODELS

GATEWAY = 'http://127.0.0.1:8789/v1'


def append(path, value):
    with path.open('a') as stream:
        stream.write(json.dumps(value, allow_nan=False)+'\n'); stream.flush()


class SampleBudget:
    """Count actual native complete() calls, including the native connectivity probe."""
    def __init__(self, maximum):
        self.maximum, self.started = maximum, 0
        self.reached = asyncio.Event()

    async def complete(self, native_complete, *args):
        if self.started >= self.maximum:
            self.reached.set()
            # Do not fabricate another response. Native run_agents cancellation
            # drains its evaluator queue and closes workers in its own finally.
            await asyncio.Future()
        self.started += 1
        return await native_complete(*args)

    async def run(self, native_coroutine):
        running = asyncio.create_task(native_coroutine)
        stop = asyncio.create_task(self.reached.wait())
        try:
            done, _ = await asyncio.wait((running, stop), return_when=asyncio.FIRST_COMPLETED)
            if stop in done and not running.done(): running.cancel()
            return await running
        finally:
            stop.cancel()
            await asyncio.gather(stop, return_exceptions=True)


def original(args, *, request_timeout=180):
    import openai
    from . import funsearch_original as driver
    if type(request_timeout) is not int or request_timeout not in (180, 330):
        raise ValueError('Only the reviewed 180/330-second request deadlines are supported')
    client = openai.OpenAI(base_url=GATEWAY, api_key=os.environ['OPENAI_API_KEY'], timeout=request_timeout, max_retries=0)
    def draw(prompt):
        response = client.chat.completions.create(model=args.model, n=1,
            messages=[{'role':'system','content':'Complete the final Python function in the supplied program. Return only its indented function body, without the def header, markdown fences or explanation. Preserve the input/output contract.'},
                      {'role':'user','content':prompt}])
        append(args.output/'gateway-calls.jsonl', {'model':args.model, 'response_id':response.id,
               'usage':response.usage.model_dump() if response.usage is not None else None})
        return response.choices[0].message.content
    with driver.native_namespace(Path.cwd()) as native:
        config = native.config_lib.Config(programs_database=native.config_lib.ProgramsDatabaseConfig(num_islands=2),
                                           num_samplers=1, num_evaluators=1, samples_per_prompt=1)
        factory = {'draw_sample':draw, 'sandbox_factory':lambda: NamespaceSandbox(args.bubblewrap,args.output),
                   'inputs':[(9,5)]}
        specification=Path('implementation/specification_nonsymmetric_admissible_set.txt').read_text()
        return driver.run_native(native,specification,factory,config,args.output,args.max_samples,32*1024**2)


async def reimplementation(args):
    from funsearch import async_agents, code_manipulation, config, core, models, programs_database, sampler
    from funsearch.utilities import parse_specfile
    os.environ['OPENAI_BASE_URL'] = GATEWAY
    os.environ['WANDB_MODE'] = 'offline'
    os.environ['WANDB_SILENT'] = 'true'
    os.environ['WANDB_DIR'] = str(args.output)
    specification = Path('examples/cap_set_spec.py').read_text()
    evolve, evaluate = core._extract_function_names(specification)
    system, specification = parse_specfile.extract_system_prompt(specification,evolve)
    template = code_manipulation.text_to_program(specification)
    conf = config.Config(num_samplers=1,num_evaluators=1,num_islands=2,samples_per_prompt=1,
                         run_duration=1800,reset_period=600,relative_cost_of_input_tokens=1.0,
                         system_prompt=system,api_call_timeout=180,api_call_max_retries=1)
    identity=uuid.uuid4().hex
    log=args.output/'native';log.mkdir()
    model=models.LLMModel(model_name='openai%'+args.model, log_path=log,system_prompt=system,id=0)
    if model.model != args.model or model.provider != 'openai':
        raise ValueError('Native provider routing changed the selected model identity')
    model.client=model.client.with_options(timeout=180,max_retries=0)
    budget=SampleBudget(args.max_samples+1)  # native validate_model call is additional
    native_complete=model.complete
    async def complete(prompt):
        response, usage = await budget.complete(native_complete,prompt)
        append(args.output/'gateway-calls.jsonl',{'index':budget.started,'model':args.model,
                'native_usage':usage.to_dict() if usage is not None else None})
        return response,usage
    model.complete=complete
    llm=sampler.LLM(1,model,log_path=log,api_call_timeout=180,api_call_max_retries=1)
    database=programs_database.ProgramsDatabase(conf.programs_database,template,evolve,identifier=identity)
    class NativeNamespaceSandbox(NamespaceSandbox):
        def __init__(self,base_path,**kwargs):super().__init__(args.bubblewrap,base_path,**kwargs)
    portable=async_agents.PortableSystemConfig(log_path=log,output_path=str(args.output),sandbox_class=NativeNamespaceSandbox,
        parsed_inputs=[6],template=template,function_to_evolve=evolve,function_to_run=evaluate,lm=[llm],
        model_identifier='openai%'+args.model,problem_name='cap_set_spec',timestamp=identity,
        name_for_saving='cap_set_'+args.model+'_'+identity,problem_identifier='cap_set_spec_'+identity,tag='arena-native-pilot')
    # Preserve native connectivity validation, with its existing timeout argument
    # set to the same explicit 180-second request deadline as the sampler.
    validate=async_agents.validate_model
    async def bounded_validation(lm,timeout=180):return await validate(lm,timeout=timeout)
    async_agents.validate_model=bounded_validation
    try:
        await budget.run(async_agents.run_agents(conf,async_agents.AsyncProgramsDatabase(database),portable))
    finally:
        async_agents.validate_model=validate
        database.backup()
        from .funsearch_original import _json_value
        leaders=[{'program':None if program is None else str(program),'score':_json_value(score)} for program,score in database.get_best_programs_per_island()]
        (args.output/'native-result.json').write_text(json.dumps({'schema':'arena.funsearch-kitft/1',
            'canonical_evaluation':False,'model':args.model,'native_complete_calls':budget.started,
            'sample_budget_reached':budget.reached.is_set(),'native_validation_call_included':True,
            'max_generated_samples':args.max_samples,'island_leaders':leaders},indent=2,allow_nan=False)+'\n')
    return 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--engine',choices=('original','reimplementation'),required=True)
    parser.add_argument('--model',choices=MODELS,required=True)
    parser.add_argument('--bubblewrap',type=Path,required=True)
    parser.add_argument('--max-samples',type=int,choices=range(1,9),default=6)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not os.environ.get('OPENAI_API_KEY'):raise ValueError('A scoped local gateway key is required')
    args.output.mkdir(parents=True,exist_ok=True)
    if any(args.output.iterdir()):raise ValueError('Pilot results directory must be empty')
    proof={'schema':'arena.funsearch-gateway-pilot/1','engine':args.engine,'model':args.model,'endpoint':GATEWAY,
           'native_search_and_scoring':True,'canonical_evaluation':False,'provider_model_alias_substituted':False,
           'generated_sample_budget':args.max_samples,'additional_native_validation_calls':int(args.engine=='reimplementation'),
           'evaluation_concurrency':1,'namespace_sandbox':{'network':False,'host_credentials_mounted':False,'address_space_bytes':2*1024**3,'wall_timeout_seconds':30},
           'task':{'kind':'constant-weight admissible set','input':[9,5]} if args.engine=='original' else {'kind':'cap set','dimension':6},
           'provider_controls_unenforced':[] if args.engine=='original' else ['temperature','top_p','max_tokens']}
    (args.output/'provider-seam.json').write_text(json.dumps(proof,indent=2)+'\n')
    return original(args) if args.engine=='original' else asyncio.run(reimplementation(args))


if __name__=='__main__':
    raise SystemExit(main())
