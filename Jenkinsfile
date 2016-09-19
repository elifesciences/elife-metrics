elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()

    stage 'Project tests'
    lock('elife-metrics--ci') {
        builderDeployRevision 'elife-metrics--ci', commit
        builderProjectTests 'elife-metrics--ci', '/srv/elife-metrics' 
    }

    stage 'Deploy on end2end'
    lock('elife-metrics--end2end') {
        builderDeployRevision 'elife-metrics--end2end', commit
        builderSmokeTests 'elife-metrics--end2end', '/srv/elife-metrics'
    }

    elifeMainlineOnly {
        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}
