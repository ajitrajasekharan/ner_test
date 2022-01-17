
function run_tests
{
    for i in `ls -1v`
    do
        if [ -d $i ]
        then
            echo "Running tests in : $i"
            (cd $i; python ../../eval_results.py -config ./eval_config.json -strict; python ../../eval_results.py -config ./eval_config.json;)
        fi
    done
}



run_tests
