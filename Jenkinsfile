elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()

    stage 'Project tests'
    lock('elife-metrics--ci') {
        builderDeployRevision 'elife-metrics--ci', commit
        builderProjectTests 'elife-metrics--ci', '/srv/elife-metrics' 
    }

    elifeMainlineOnly {
        stage 'End2end tests'
        lock('elife-metrics--end2end') {
            elifeEnd2EndTest({
                builderDeployRevision 'elife-metrics--end2end', commit
                builderSmokeTests 'elife-metrics--end2end', '/srv/elife-metrics'
            }, 'metrics')
        }

        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}
