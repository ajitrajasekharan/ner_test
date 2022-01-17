
function run_tests
{
    for i in `ls -1v`
    do
        if [ -d $i ]
        then
            echo "Generating sentences in : $i"
            (cd $i; python ../../extract_sentences.py -config ./extract_config.json)
        fi
    done
}



run_tests
