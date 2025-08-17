import { Logger } from '../logger';

/**
 * Extract LinkedIn data from evaluation result
 */
export function extractLinkedinData(result: string): string | null {
  Logger.debug("🔍 Attempting to extract LinkedIn data from string of length:", result.length);
  
  // Try different pattern variations that might appear in the text
  let patterns = [
    /\[LINKEDIN_DATA\]([\s\S]*?)\[END_LINKEDIN_DATA\]/,
    /\[LINKEDIN_DATA\]\s*([\s\S]*?)\s*\[END_LINKEDIN_DATA\]/,
    /\[LINKEDIN_DATA\]\n([\s\S]*?)\n\[END_LINKEDIN_DATA\]/,
    /\[LINKEDIN_DATA\][\r\n]+([\s\S]*?)[\r\n]+\[END_LINKEDIN_DATA\]/
  ];
  
  // Try each pattern
  for (const pattern of patterns) {
    const match = result.match(pattern);
    if (match && match[1]) {
      Logger.debug("🔍 LinkedIn data match found with pattern:", pattern);
      Logger.debug("🔍 LinkedIn data extracted, length:", match[1].trim().length);
      return match[1].trim();
    }
  }
  
  // If we got here, no match was found
  Logger.debug("🔍 LinkedIn data not found with any pattern");
  
  // Log a small excerpt to help debug
  const excerpt = result.substring(0, 200);
  Logger.debug("🔍 First 200 chars of content:", excerpt);
  
  // If result contains [LINKEDIN_DATA] but we couldn't extract it, log the position
  const marker = "[LINKEDIN_DATA]";
  const endMarker = "[END_LINKEDIN_DATA]";
  const markerIndex = result.indexOf(marker);
  const endMarkerIndex = result.indexOf(endMarker);
  
  if (markerIndex !== -1) {
    Logger.debug(`🔍 Found [LINKEDIN_DATA] at position ${markerIndex}, content around it:`, 
      result.substring(Math.max(0, markerIndex - 20), markerIndex + marker.length + 50));
      
    if (endMarkerIndex !== -1) {
      Logger.debug(`🔍 Found [END_LINKEDIN_DATA] at position ${endMarkerIndex}`);
      Logger.debug(`🔍 Distance between markers: ${endMarkerIndex - (markerIndex + marker.length)}`);
    } else {
      Logger.debug("🔍 End marker [END_LINKEDIN_DATA] not found");
    }
  }
  
  return null;
}

/**
 * Extract enrichment logs from evaluation result
 */
export function extractEnrichmentLogs(result: string): string | null {
  Logger.debug("📋 Attempting to extract enrichment logs from string of length:", result.length);
  
  // Try different pattern variations that might appear in the text
  let patterns = [
    /\[ENRICHMENT LOG\]([\s\S]*?)\[END ENRICHMENT LOG\]/,
    /\[ENRICHMENT LOG\]\s*([\s\S]*?)\s*\[END ENRICHMENT LOG\]/,
    /\[ENRICHMENT LOG\]\n([\s\S]*?)\n\[END ENRICHMENT LOG\]/,
    /\[ENRICHMENT LOG\][\r\n]+([\s\S]*?)[\r\n]+\[END ENRICHMENT LOG\]/
  ];
  
  // Try each pattern
  for (const pattern of patterns) {
    const match = result.match(pattern);
    if (match && match[1]) {
      Logger.debug("📋 Enrichment logs found with pattern:", pattern);
      Logger.debug("📋 Enrichment logs extracted, length:", match[1].trim().length);
      return match[1].trim();
    }
  }
  
  Logger.debug("📋 No enrichment logs found");
  return null;
}

/**
 * Extract PDF resume data from evaluation result
 */
export function extractPdfResumeData(result: string): string | null {
  Logger.debug("📄 Attempting to extract PDF resume data from string of length:", result.length);
  
  // Try different pattern variations that might appear in the text
  let patterns = [
    /\[PDF_RESUME_DATA\]([\s\S]*?)\[END_PDF_RESUME_DATA\]/,
    /\[PDF_RESUME_DATA\]\s*([\s\S]*?)\s*\[END_PDF_RESUME_DATA\]/,
    /\[PDF_RESUME_DATA\]\n([\s\S]*?)\n\[END_PDF_RESUME_DATA\]/,
    /\[PDF_RESUME_DATA\][\r\n]+([\s\S]*?)[\r\n]+\[END_PDF_RESUME_DATA\]/
  ];
  
  // Try each pattern
  for (const pattern of patterns) {
    const match = result.match(pattern);
    if (match && match[1]) {
      Logger.debug("📄 PDF resume data match found with pattern:", pattern);
      Logger.debug("📄 PDF resume data extracted, length:", match[1].trim().length);
      return match[1].trim();
    }
  }
  
  // If we got here, no match was found
  Logger.debug("📄 PDF resume data not found with any pattern");
  
  // Log a small excerpt to help debug
  const excerpt = result.substring(0, 200);
  Logger.debug("📄 First 200 chars of content:", excerpt);
  
  // If result contains [PDF_RESUME_DATA] but we couldn't extract it, log the position
  const marker = "[PDF_RESUME_DATA]";
  const endMarker = "[END_PDF_RESUME_DATA]";
  const markerIndex = result.indexOf(marker);
  const endMarkerIndex = result.indexOf(endMarker);
  
  if (markerIndex !== -1) {
    Logger.debug(`📄 Found [PDF_RESUME_DATA] at position ${markerIndex}, content around it:`, 
      result.substring(Math.max(0, markerIndex - 20), markerIndex + marker.length + 50));
      
    if (endMarkerIndex !== -1) {
      Logger.debug(`📄 Found [END_PDF_RESUME_DATA] at position ${endMarkerIndex}`);
      Logger.debug(`📄 Distance between markers: ${endMarkerIndex - (markerIndex + marker.length)}`);
    } else {
      Logger.debug("📄 End marker [END_PDF_RESUME_DATA] not found");
    }
  }
  
  return null;
}

/**
 * Extract multi-axis scores from eval result
 */
export function extractMultiAxisData(result: string, axisScores?: Array<{name: string, score: number | null}>): string | null {
  // If we have axis scores directly, format them
  if (axisScores && Array.isArray(axisScores)) {
    try {
      // Format multi-axis scores as readable text
      let formattedData = "## Multi-Axis Evaluation Scores\n\n";
      
      axisScores.forEach(axis => {
        formattedData += `### ${axis.name}\n`;
        formattedData += `Score: ${axis.score !== null ? axis.score : 'Not available'}\n\n`;
      });
      
      return formattedData;
    } catch (e) {
      console.error('Error formatting multi-axis data:', e);
      return JSON.stringify(axisScores, null, 2);
    }
  }
  
  // As a fallback, try to extract from the result text
  const multiAxisMatch = result.match(/\[MULTI_AXIS_SCORES\]([\s\S]*?)\[END_MULTI_AXIS_SCORES\]/);
  
  if (multiAxisMatch && multiAxisMatch[1]) {
    // Clean up the data and format it
    let multiAxisData = multiAxisMatch[1].trim();
    
    try {
      // Try to parse as JSON for prettier formatting
      const parsedData = JSON.parse(multiAxisData);
      return JSON.stringify(parsedData, null, 2);
    } catch (e) {
      // If it's not valid JSON, just return the raw text
      return multiAxisData;
    }
  }
  
  return null;
}


