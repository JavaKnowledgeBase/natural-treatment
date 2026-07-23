package app.rootwell.orchestrator;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrchestratorController {

    private final OrchestratorService orchestratorService;

    public OrchestratorController(OrchestratorService orchestratorService) {
        this.orchestratorService = orchestratorService;
    }

    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/sessions")
    public Map<String, Object> createSession(@RequestBody(required = false) CreateSessionRequest req) {
        return orchestratorService.createSession(req != null ? req.language() : null);
    }

    @GetMapping("/sessions/{sid}/state")
    public Map<String, Object> getState(@PathVariable String sid) {
        return orchestratorService.getState(sid);
    }

    @PostMapping("/sessions/{sid}/message")
    public Map<String, Object> postMessage(@PathVariable String sid, @RequestBody MessageRequest req) {
        return orchestratorService.postMessage(sid, req);
    }

    @PostMapping("/sessions/{sid}/add-item")
    public Map<String, Object> addItem(@PathVariable String sid, @RequestBody AddItemRequest req) {
        return orchestratorService.addItem(sid, req);
    }

    @PostMapping("/sessions/{sid}/remove-item")
    public Map<String, Object> removeItem(@PathVariable String sid, @RequestBody RemoveItemRequest req) {
        return orchestratorService.removeItem(sid, req);
    }

    @PostMapping("/sessions/{sid}/advance-to-causes")
    public Map<String, Object> advanceToCauses(@PathVariable String sid) {
        return orchestratorService.advanceToCauses(sid);
    }

    @PostMapping("/sessions/{sid}/analyze")
    public Map<String, Object> analyze(@PathVariable String sid) {
        return orchestratorService.analyze(sid);
    }

    @PostMapping("/sessions/{sid}/email/request")
    public Map<String, Object> emailRequest(@PathVariable String sid, @RequestBody EmailRequestBody req) {
        return orchestratorService.emailRequest(sid, req);
    }

    @PostMapping("/sessions/{sid}/email/confirm")
    public Map<String, Object> emailConfirm(@PathVariable String sid, @RequestBody EmailConfirmBody req) {
        return orchestratorService.emailConfirm(sid, req);
    }

    @PostMapping("/sessions/{sid}/end")
    public Map<String, Object> endSession(@PathVariable String sid) {
        return orchestratorService.endSession(sid);
    }
}
