# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

class AISybilOracle(gl.Contract):
    verification_criteria: str
    verified_users_json: str
    total_verified: u256

    def __init__(self, verification_criteria: str):
        self.verification_criteria = verification_criteria
        self.verified_users_json = "[]"
        self.total_verified = u256(0)

    @gl.public.write
    def verify_identity(self, profile_url: str) -> str:
        caller = gl.message.sender
        
        verified_list = json.loads(self.verified_users_json)
        if caller in verified_list:
            raise gl.vm.UserError("Caller is already verified as human.")

        criteria = self.verification_criteria

        def evaluate_proof() -> dict:
            try:
                web_data = gl.nondet.web.render(profile_url, mode="text")
                if not web_data or len(web_data) < 10:
                    return {"is_human": False, "error": True, "reason": "Failed to fetch valid profile data."}
            except Exception:
                return {"is_human": False, "error": True, "reason": "Network fetch error."}

            # الاستغناء عن f-strings المتعددة الأسطر لتجنب أخطاء محرك GenVM
            task = (
                "You are a strict Sybil-resistance AI Oracle.\n"
                "Verification Criteria: " + criteria + "\n"
                "User Address attempting verification: " + caller + "\n\n"
                "Profile Data found at URL:\n"
                + str(web_data[:2000]) + "\n\n"
                "Does the profile explicitly contain the exact User Address and meet all the verification criteria?\n"
                "Respond using ONLY the following JSON format:\n"
                '{"is_human": bool, "reason": "short explanation"}'
            )

            try:
                result_str = gl.nondet.exec_prompt(task).replace("```json", "").replace("```", "")
                parsed = json.loads(result_str)
                if "is_human" not in parsed:
                    return {"is_human": False, "error": True, "reason": "Invalid LLM JSON format."}
                parsed["error"] = False
                return parsed
            except Exception:
                return {"is_human": False, "error": True, "reason": "LLM execution or parsing failed."}

        consensus_result = gl.eq_principle.strict_eq(evaluate_proof)

        if consensus_result.get("error"):
            raise gl.vm.UserError("Verification process failed: " + str(consensus_result.get('reason')))

        if consensus_result["is_human"]:
            verified_list.append(caller)
            self.verified_users_json = json.dumps(verified_list)
            self.total_verified += u256(1)
            return "Verification SUCCESS. " + caller + " is registered as human. Reason: " + str(consensus_result.get('reason'))
        else:
            return "Verification FAILED. Reason: " + str(consensus_result.get('reason'))

    @gl.public.view
    def is_verified(self, address: str) -> bool:
        verified_list = json.loads(self.verified_users_json)
        return address in verified_list