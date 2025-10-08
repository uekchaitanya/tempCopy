from flask import render_template, request, jsonify
from app import app
import os
import sys
from pathlib import Path

# Fix import path - add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import MarginBot
try:
    from v1.core import MarginBot
except ImportError:
    # If v1 is inside app directory
    try:
        from app.v1.core import MarginBot
    except ImportError:
        raise ImportError(
            "Cannot find MarginBot. Please ensure:\n"
            "1. v1/__init__.py exists\n"
            "2. v1/core.py contains MarginBot class\n"
            "3. v1 directory is in the correct location"
        )

@app.route('/')
def index():
    """Render the main UI"""
    return render_template('index.html')


@app.route('/outlierv1', methods=['GET', 'POST'])
def outlierv1():
    """
    Enhanced outlier detection endpoint with parameter support
    Accepts parameters from UI form and returns structured results
    """
    if request.method == 'GET':
        # Return simple form or status for GET requests
        return jsonify({
            'status': 'ready',
            'message': 'Submit POST request with parameters'
        })
    
    try:
        # Hardcoded paths for MVP
        csv_path = 'data/sample_summary.csv'
        out_csv = 'out/outliers_rules.csv'
        
        # Extract parameters from form data
        mode = request.form.get('mode', 'rules')
        center = request.form.get('center', 'NPM')
        action = request.form.get('action', 'analyze')  # Get the action type
        
        # Advanced parameters
        abs_threshold = float(request.form.get('abs_threshold', 5000000))
        pct_threshold = float(request.form.get('pct_threshold', 0.25))
        z_threshold = float(request.form.get('z_threshold', 3.0))
        top_n = int(request.form.get('top_n', 20))
        
        # Validate CSV path exists
        if not os.path.exists(csv_path):
            return jsonify({
                'success': False,
                'error': f'CSV file not found: {csv_path}'
            }), 400
        
        # Ensure output directory exists
        out_dir = os.path.dirname(out_csv)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        # Initialize bot
        bot = MarginBot()
        
        # Run outlier detection based on mode and action
        if mode == 'rules':
            # Call outliers method with parameters
            result = bot.outliers(
                csv_path=csv_path,
                center=center,
                abs_threshold=abs_threshold,
                pct_threshold=pct_threshold,
                z_threshold=z_threshold,
                top_n=top_n,
                out_csv=out_csv
            )
        
        elif mode == 'ai':
            # Placeholder for AI-based mode
            return jsonify({
                'success': False,
                'error': 'AI-based mode is not yet implemented'
            }), 501
        
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid mode: {mode}'
            }), 400
        
        # Parse results based on action
        response_data = {
            'success': True,
            'mode': mode,
            'center': center,
            'output_file': out_csv,
            'action': action,
            'csv_url': f'/download/{os.path.basename(out_csv)}'  # Add download URL
        }
        
        # Add result data if available
        if isinstance(result, dict):
            response_data.update({
                'flagged_count': result.get('flagged_count', 0),
                'total_count': result.get('total_count', 0),
                'dates_analyzed': result.get('dates_analyzed', ''),
                'top_outliers': result.get('top_outliers', [])
            })
        elif isinstance(result, list):
            # Convert list to structured format
            top_outliers = []
            for r in result[:top_n]:
                if isinstance(r, dict):
                    top_outliers.append(r)
                else:
                    # If result is not dict, try to parse it
                    top_outliers.append({'data': str(r)})
            
            response_data.update({
                'top_outliers': top_outliers,
                'total_count': len(result),
                'flagged_count': sum(1 for r in result if isinstance(r, dict) and r.get('flag'))
            })
        
        # If MarginBot returns raw data, read the CSV and parse it
        if os.path.exists(out_csv):
            import csv
            with open(out_csv, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Get summary info
                if not response_data.get('total_count'):
                    response_data['total_count'] = len(rows)
                
                if not response_data.get('flagged_count'):
                    flagged = sum(1 for row in rows if row.get('FLAG', '').lower() in ['true', '1', 'yes', '✓'])
                    response_data['flagged_count'] = flagged
                
                # Get top outliers if not already set
                if not response_data.get('top_outliers'):
                    top_outliers = []
                    for row in rows[:top_n]:
                        outlier = {
                            'header': row.get('HEADER', row.get('header_account_id', 'N/A')),
                            'applied_t1': float(row.get('APPLIED_t1', 0)) if row.get('APPLIED_t1') else None,
                            'applied_t': float(row.get('APPLIED_t', 0)) if row.get('APPLIED_t') else None,
                            'delta': float(row.get('Δ', row.get('delta', 0))) if row.get('Δ', row.get('delta')) else None,
                            'pct_change': float(row.get('%Δ', row.get('pct_change', 0))) if row.get('%Δ', row.get('pct_change')) else None,
                            'z_score': float(row.get('Z', row.get('z_score', 0))) if row.get('Z', row.get('z_score')) else None,
                            'flag': row.get('FLAG', row.get('flag', 'false')).lower() in ['true', '1', 'yes', '✓']
                        }
                        top_outliers.append(outlier)
                    response_data['top_outliers'] = top_outliers
        
        return jsonify(response_data)
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter value: {str(e)}'
        }), 400
    
    except Exception as e:
        import traceback
        print("Error traceback:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500


@app.route('/explain', methods=['POST'])
def explain():
    """
    Separate endpoint for policy-level explanation
    """
    try:
        csv_path = request.form.get('csv_path', 'data/sample_summary.csv')
        center = request.form.get('center', 'NPM')
        header = request.form.get('header')
        
        if not header:
            return jsonify({
                'success': False,
                'error': 'Header account ID is required'
            }), 400
        
        bot = MarginBot()
        explanation = bot.explain_summary(
            csv_path=csv_path,
            center=center,
            header=header
        )
        
        return jsonify({
            'success': True,
            'center': center,
            'header': header,
            'explanation': explanation
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Legacy route for backward compatibility
@app.route('/outlier', methods=['GET', 'POST'])
def outlier():
    """
    Legacy endpoint with hardcoded values
    Redirects to new endpoint
    """
    return outlierv1()


@app.route('/download/<filename>')
def download_file(filename):
    """
    Download CSV file from output directory
    """
    try:
        from flask import send_from_directory
        
        # Security: Only allow downloads from 'out' directory
        safe_filename = os.path.basename(filename)  # Prevent directory traversal
        output_dir = os.path.join(os.getcwd(), 'out')
        
        file_path = os.path.join(output_dir, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_from_directory(
            output_dir,
            safe_filename,
            as_attachment=True,
            download_name=safe_filename
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
