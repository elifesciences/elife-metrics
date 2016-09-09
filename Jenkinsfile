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
        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}
