package app.rootwell.email;

import com.fasterxml.jackson.annotation.JsonProperty;

/** A herb-sourcing inquiry from the "not sure where to find this" link in the
 * herb detail modal -- not tied to a session, no verification gate (it sends
 * TO us, not to an arbitrary address supplied by the caller). */
public record ContactRequest(
        String name, String email, @JsonProperty("herb_name") String herbName, String message) {}
