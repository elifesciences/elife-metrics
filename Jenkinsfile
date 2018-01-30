elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }

    stage 'Project tests', {
        lock('elife-metrics--ci') {
            builderDeployRevision 'elife-metrics--ci', commit
            builderProjectTests 'elife-metrics--ci', '/srv/elife-metrics' 
        }
    }

    elifeMainlineOnly {
        stage 'End2end tests', {
            elifeSpectrum(
                deploy: [
                    stackname: 'elife-metrics--end2end',
                    revision: commit,
                    folder: '/srv/elife-metrics'
                ],
                marker: 'metrics'
            )
        }

        stage 'Deploy on continuumtest', {
            lock('elife-metrics--continuumtest') {
                builderDeployRevision 'elife-metrics--continuumtest', commit
                builderSmokeTests 'elife-metrics--continuumtest', '/srv/elife-metrics'
            }
        }

        stage 'Approval', {
            elifeGitMoveToBranch commit, 'approved'
        }
    }
}
