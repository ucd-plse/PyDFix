class FinalOutcome:
    FAILED_INFO_EXTRACTION_FROM_LOG_FILENM = 'Unable to extract details from log file name'
    FAILED_SOURCE_CODE_CLONE = 'Failed to checkout source code'
    FAILED_BUILD_SCRIPT_COPY = 'Failed to copy build script'
    FAILED_GET_COMMIT_DATE = 'Failed to get commit date'
    FAILED_NO_BUILD_OUTCOME = 'No build outcome'
    FAILED_ERROR = 'Encountered error: {}'
    FAILED_UNABLE_TO_MODIFY_TRAVIS_YML = 'Unable to modify .travis.yml'
    FAILED_TO_PREPARE_BUILD_SCRIPT = 'Failed to prepare build script'
    FAILED_TO_RUN_DOCKER = 'Failed to run docker container'
    PARTIAL_EXHAUSTED_ALL_OPTIONS = 'Exhausted all options'
    PARTIAL_NO_POSSIBLE_CANDIDATES = 'No possible candidates'
    SUCCESS_FIXED_BUILD = 'Successfully fixed build'
    SUCCESS_NO_LONGER_DEPENDENCY_ERROR = 'No longer recognized as a dependency error'
    SUCCESS_RESTORED_TO_ORIGINAL_STATUS = 'Restored to original status'
    SUCCESS_RESTORED_TO_ORIGINAL_ERROR = 'Restored to original error'
