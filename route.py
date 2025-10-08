from flask import render_template, request, jsonify
from app import app
from v1.core import MarginBot
import os

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
        # Extract parameters from form data
        mode = request.form.get('mode', 'rules')
        center = request.form.get('center', 'NPM')
        header = request.form.get('header', None)  # Optional
        csv_path = request.form.get('csv_path', 'data/sample_summary.csv')
        out_csv = request.form.get('out_csv', 'out/outliers_rules.csv')
        
        # Advanced parameters
        abs_threshold = float(request.form.get('abs_threshold', 5000000))
        pct_threshold = float(request.form.get('pct_threshold', 0.25))
        z_threshold = float(request.form.get('z_threshold', 3.0))
        top_n = int(request.form.get('top_n', 20))
        
        query = request.form.get('query', '')
        
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
        
        # Run outlier detection based on mode
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
            
            # If header is specified, also get explanation
            explanation = None
            if header:
                explanation = bot.explain_summary(
                    csv_path=csv_path,
                    center=center,
                    header=header
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
        
        # Parse results (assumes bot returns structured data)
        # Adjust this based on your actual MarginBot return structure
        response_data = {
            'success': True,
            'mode': mode,
            'center': center,
            'output_file': out_csv,
            'query': query
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
            response_data.update({
                'top_outliers': result[:top_n],
                'total_count': len(result),
                'flagged_count': sum(1 for r in result if r.get('flag'))
            })
        
        # Add explanation if header was specified
        if header and explanation:
            response_data['explanation'] = explanation
        
        return jsonify(response_data)
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter value: {str(e)}'
        }), 400
    
    except Exception as e:
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
