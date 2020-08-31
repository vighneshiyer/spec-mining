use std::fs::File;
use std::io::{BufRead, BufReader, Result};
use ego_tree::{Tree, NodeMut, NodeRef};

#[derive(Debug)]
/*
struct Module<'a> {
    name: String,
    children: Vec<&'a Module<'a>>
}
*/

struct Module {
    name: String, // use String instead of &str to gain ownership
    //children: Vec<Box<Module>>,
    //parent: Option<&Box<Module>>
}

/*
impl<'a> Module<'a> {
    fn empty(name: String) -> Module<'a> {
        Module{name: name, children: Vec::new()}
    }
}
*/

impl Module {
    /*
    fn empty(name: String) -> Module {
        Module{name: name, children: Vec::new()}
    }
    */

    /*
    fn empty_with_parent(name: String, parent: Box<Module>) -> Module {
        Module{name: name, children: Vec::new(), parent: Some(parent)}
    }
    */
}

fn main() -> Result<()> {
    //let file = File::open("/home/vighnesh/20-research/23-projects/10-spec_mining/spec-mining/vcd/gcd/GCD.vcd").expect("File not found");
    let file = File::open("/home/vighnesh/20-research/24-repos/riscv-mini/outputs_gold/rv32ui-p-add.vcd").expect("File not found");
    //let file = File::open("/home/vighnesh/20-research/24-repos/riscv-mini/outputs_gold/multiply.riscv.vcd").expect("File not found");

    let mut module_tree = Tree::new(Module{name: "TOP".to_string()});
    let mut current_module = module_tree.root_mut();
    let mut timescale: Option<String> = None;

    for line in BufReader::new(file).lines() {
        let line = line?;
        let line = line.trim();
        let mut split = line.split_whitespace();
        match split.next() {
            Some("$timescale") => {
                timescale = Some(split.next().expect("VCD $timescale not followed up with a valid timescale").to_string());
            }
            Some("$scope") => {
                let scope_spec = split.next().expect("$scope should be followed by a specifier");
                assert_eq!(scope_spec, "module");
                let module_name = split.next().expect("$scope specifier should be followed by a name");
                let this_module = Module{name: module_name.to_string()};
                //module_tree.nodes().last().append(this_module);
                let new_node = current_module.append(this_module);
                //current_module = new_node; // Illegal because current_module is mutably borrowed so can't be overwritten
                /*
                let this_module = Box::new(Module::empty(module_name.to_string()));
                if module_tree.len() == 0 {
                    module_tree.push(this_module);
                } else {
                    let parent_module = module_tree.last().unwrap();
                    parent_module.children.push(this_module);
                    module_tree.push(this_module);
                }
                */
            }
            Some("$upscope") => {

            }
            _ => ()
        }
    }
    println!("VCD timescale {:?}", timescale);
    println!("Module tree: {:#?}", module_tree);
    Ok(())
    //let contents = fs::read_to_string(filename)
        //.expect("Something went wrong reading the file");
    //println!("With text:\n{}", contents);
}
