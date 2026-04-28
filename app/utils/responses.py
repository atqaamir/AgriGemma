class ExecutionResponse:

    @staticmethod
    def success(message, data=None):

        return {
            "execution_status": "success",
            "message": message,
            "data": data,
        }

    @staticmethod
    def failure(message, error=None):

        return {
            "execution_status": "failed",
            "message": message,
            "error": error,
        }